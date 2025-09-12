# src/ingest/document_analyzer.py
from __future__ import annotations
import os, json, re, asyncio, hashlib
from typing import Any, Dict, List, Tuple, Optional, Type
from datetime import datetime, timezone

try:
    import httpx
    from redis import asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    httpx = None
    aioredis = None

from ..api.schemas import AnalysisResult, Suggestion, AnalysisMode
from ..common.logging import get_logger

log = get_logger("document_analyzer")

try:
    from opentelemetry import trace
    TR = trace.get_tracer(__name__)
except ImportError:
    # Mock tracer if OpenTelemetry not available
    class MockSpan:
        def set_attribute(self, key, value): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
    
    class MockTracer:
        def start_as_current_span(self, name): return MockSpan()
    
    TR = MockTracer()

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
REDIS_TTL_SECONDS = int(os.getenv("ANALYSIS_CACHE_TTL", "604800"))  # 7 days
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
ANALYSIS_DEFAULT_MODE: AnalysisMode = os.getenv("ANALYSIS_MODE", "fast")  # fast|smart|deep

_redis = None
if REDIS_AVAILABLE:
    try:
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    except Exception as e:
        log.warning(f"Redis connection failed: {e}")

ANCHORS = (" shall ", " must ", " required ", " require ", " should ")

def _doc_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

async def _redis_get(key: str, model: Optional[Type] = None) -> Any:
    if not _redis:
        return None
    try:
        raw = await _redis.get(key)
        if not raw:
            return None
        # aioredis may return bytes unless decode_responses=True
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8", errors="replace")
        if model and hasattr(model, 'model_validate_json'):
            # Pydantic v2: parse JSON string into a model
            return model.model_validate_json(raw)
        return json.loads(raw)
    except Exception as e:
        log.warning(f"Redis get failed: {e}")
        return None

async def _redis_set(key: str, value: Any, ttl: int = REDIS_TTL_SECONDS) -> None:
    if not _redis:
        return
    try:
        # Handle Pydantic models and datetime objects properly
        if hasattr(value, 'model_dump_json'):
            # Pydantic v2: JSON string with datetimes in ISO 8601
            payload = value.model_dump_json()
        elif hasattr(value, 'model_dump'):
            # Pydantic model - use JSON mode to handle datetimes
            payload = json.dumps(value.model_dump(mode='json'), separators=(',', ':'))
        else:
            # Handle datetime objects generically
            def _json_default(obj):
                if hasattr(obj, 'isoformat'):
                    return obj.isoformat()
                if hasattr(obj, 'model_dump'):
                    return obj.model_dump(mode='json')
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            payload = json.dumps(value, default=_json_default, separators=(',', ':'))
        
        await _redis.set(key, payload, ex=ttl)
    except Exception as e:
        log.warning(f"Redis set failed: {e}")

async def analyze_document_content(
    source_id: str,
    full_text: str,
    chunks: List[Dict[str, Any]],
    mode: Optional[AnalysisMode] = None,
    lang_hint: Optional[str] = None
) -> AnalysisResult:
    """
    Multi-tier analyzer:
    - fast: deterministic structure/anchors (no LLM)
    - smart: fast + light LLM pass over selected spans
    - deep: fast + broader LLM on a summarized map
    """
    mode = mode or ANALYSIS_DEFAULT_MODE
    started = datetime.now(timezone.utc)
    h = _doc_hash(full_text)
    rkey = f"da:{h}:{mode}"

    with TR.start_as_current_span("analysis") as sp:
        sp.set_attribute("source_id", source_id)
        sp.set_attribute("mode", mode)
        sp.set_attribute("hash", h)

        cached = await _redis_get(rkey, AnalysisResult)
        if cached:
            log.info(f"Using cached analysis for {source_id}")
            if isinstance(cached, AnalysisResult):
                return cached
            else:
                return AnalysisResult(**cached, ready=True)

        # ---- FAST LAYER (deterministic)
        topics, questions_fast, conf_fast = _fast_understanding(full_text, chunks, source_id)

        if mode == "fast":
            # Generate overview for fast mode (deterministic)
            from ..analysis.overview import build_overview
            overview_result = await build_overview(source_id, chunks, mode="fast")
            
            result = AnalysisResult(
                source_id=source_id, mode=mode, lang=lang_hint or "en",
                summary=_cap_summary(_extract_intro(full_text)),
                topics=topics, questions=[q.model_dump() for q in questions_fast],
                confidence=conf_fast, ready=True,
                started_at=started.isoformat(), completed_at=datetime.now(timezone.utc).isoformat()
            )
            # Add overview to result
            result_dict = result.model_dump()
            result_dict["overview"] = overview_result.get("overview")
            result_dict["mode_used"] = overview_result.get("mode_used", mode)
            
            await _redis_set(rkey, result_dict)
            return AnalysisResult(**result_dict)

        # ---- SMART/DEEP LLM LAYER (optional, offline-first via Ollama)
        llm_input = _pick_spans(full_text, chunks, budget_chars=8000 if mode=="smart" else 16000)
        summary_llm, q_llm, conf_llm = await _ollama_summarize_and_questions(llm_input, mode=mode, source_id=source_id)
        
        # Generate overview for smart/deep modes
        from ..analysis.overview import build_overview
        overview_result = await build_overview(source_id, chunks, mode=mode)
        
        result = AnalysisResult(
            source_id=source_id, mode=mode, lang=lang_hint or "en",
            summary=summary_llm or _cap_summary(_extract_intro(full_text)),
            topics=topics,
            questions=[q.model_dump() for q in (q_llm or questions_fast)],
            confidence=conf_llm or conf_fast,
            ready=True, started_at=started.isoformat(), completed_at=datetime.now(timezone.utc).isoformat()
        )
        # Add overview to result
        result_dict = result.model_dump()
        result_dict["overview"] = overview_result.get("overview")
        result_dict["mode_used"] = overview_result.get("mode_used", mode)
        
        await _redis_set(rkey, result_dict)
        return AnalysisResult(**result_dict)

def _extract_intro(text: str, max_chars: int = 1200) -> str:
    return text[:max_chars].strip()

def _cap_summary(s: str, cap_words: int = 120) -> str:
    words = re.findall(r"\S+", s)
    if len(words) <= cap_words: return s
    return " ".join(words[:cap_words]) + "…"

def _fast_understanding(full_text: str, chunks: List[Dict[str, Any]], source_id: str) -> Tuple[List[str], List[Suggestion], float]:
    topics = _simple_topics(full_text)
    qs = _simple_questions(topics)
    # Executable objects with boost_keywords & focus_source set later
    suggestions = [Suggestion(
        text=q,
        source_id=source_id,
        confidence=0.65
    ) for q in qs]
    return topics, suggestions, 0.7

def _simple_topics(text: str) -> List[str]:
    hints = []
    for k in ("internal control","ICFR","CAM","audit report","ESEF","tagging","Form QC","quality control"):
        if k.lower() in text.lower(): hints.append(k)
    return list(dict.fromkeys(hints))[:8]

def _simple_questions(topics: List[str]) -> List[str]:
    base = []
    for t in topics:
        if t.lower() in ("internal control","icfr"):
            base.append("What are the auditor's ICFR responsibilities as stated in this document?")
            base.append("Which ICFR requirements use 'shall' or 'must' language in this document?")
        elif t.lower() in ("form qc","quality control"):
            base.append("What are the required QC 1000 evaluation and Form QC filing dates?")
        elif t.lower() in ("cam","audit report"):
            base.append("What must be included in the auditor's report when communicating CAMs?")
    if not base:
        base.append("Summarize the objective and scope of this document.")
        base.append("List the key requirements that use 'shall', 'must', or 'required'.")
    return base[:5]

def _infer_type_from_question(q: str) -> str:
    ql = q.lower()
    if "must" in ql or "shall" in ql or "required" in ql: return "requirement"
    if "define" in ql or "definition" in ql: return "definition"
    if "exception" in ql: return "exception"
    if "process" in ql or "how to" in ql: return "process"
    return "other"

def _pick_spans(full_text: str, chunks: List[Dict[str, Any]], budget_chars: int) -> str:
    # Favor anchor-dense spans
    joiner = "\n\n---\n\n"
    ranked = sorted(chunks, key=lambda c: sum(term in c.get("text","").lower() for term in (" shall "," must "," required ")), reverse=True)
    cat = []
    cur = 0
    for ch in ranked:
        t = ch.get("text","").strip()
        if not t: continue
        if cur + len(t) + len(joiner) > budget_chars: break
        cat.append(t); cur += len(t) + len(joiner)
    if not cat:
        return full_text[:budget_chars]
    return joiner.join(cat)

async def _ollama_summarize_and_questions(context: str, mode: AnalysisMode, source_id: str) -> Tuple[str, List[Suggestion], float]:
    # Local, offline-first LLM call; we request strict JSON with schema below.
    if not httpx:
        log.warning("httpx not available, falling back to fast mode")
        return _cap_summary(context, 120), [], 0.6
        
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": OLLAMA_PROMPT_TEMPLATE.format(context=context),
        "stream": False,  # disable streaming; we want a single JSON blob
        "options": {"temperature": 0.1}
    }
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        log.warning(f"Ollama request failed: {e}")
        return _cap_summary(context, 120), [], 0.6
    
    # Ollama returns {"response": "..."}; extract JSON substring
    text = data.get("response","")
    m = re.search(r"\{[\s\S]*\}\s*$", text)  # last JSON object in response
    if not m:
        # fallback: return minimal content
        log.warning("Failed to parse JSON from Ollama response")
        return _cap_summary(context, 120), [], 0.6
    
    try:
        parsed = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        log.warning(f"JSON decode error: {e}")
        return _cap_summary(context, 120), [], 0.6
    
    summary = parsed.get("summary") or _cap_summary(context, 120)
    topics = parsed.get("topics") or []
    questions = []
    for q in parsed.get("questions", [])[:5]:
        questions.append(Suggestion(
            question=q.get("question",""),
            expected_evidence_type=q.get("expected_evidence_type"),
            boost_terms=q.get("boost_terms") or ["shall","must","required"],
            category=q.get("category") or "Specific requirements",
            confidence=q.get("confidence") or 0.8,
            focus_source_id=source_id
        ))
    conf = float(parsed.get("confidence", 0.8))
    return summary, questions, conf

# Minimal, safe prompt: requests strict JSON and forbids uncited content
OLLAMA_PROMPT_TEMPLATE = """You are an expert financial reporting/audit document analyst.
Read ONLY the passages below and produce STRICT JSON with this schema:

{{
  "summary": "<<=120 words plain text>>",
  "topics": ["<topic>", "..."],
  "questions": [
    {{
      "question": "<context-specific, executable question>",
      "expected_evidence_type": "requirement|definition|exception|process|other",
      "boost_terms": ["shall","must","required"],
      "category": "About this document|Specific requirements|Common inquiries",
      "confidence": 0.0-1.0
    }}
  ],
  "confidence": 0.0-1.0
}}

Do NOT include explanations outside JSON. Use ONLY the provided context. If unsure, lower confidence.

Context:
\"\"\"{context}\"\"\"
"""
