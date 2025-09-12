"""Compose grounded answers with LLM synthesis (evidence-bound, no hallucinations)."""
import json
import os
from typing import Dict, List, Any, Optional
from ..common.constants import MAX_CITATION_SNIPPET_CHARS, NO_CITATION_NO_CLAIM
from ..common.logging import get_logger

try:
    from opentelemetry import trace
    tr = trace.get_tracer("citespine")
except ImportError:
    class MockTracer:
        def start_as_current_span(self, name):
            class MockSpan:
                def __enter__(self): return self
                def __exit__(self, *args): pass
            return MockSpan()
    tr = MockTracer()

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

log = get_logger("answer/compose")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")

# Prompt A - Answer Synthesis (LLM)
ANSWER_SYSTEM_PROMPT = """You are a compliance-grade assistant. Answer the user's QUESTION using ONLY the provided EVIDENCE_SPANS.
No citation → no claim. Do not invent facts. Keep to ≤500 words.
Output STRICT JSON only.
Schema:
{
  "answer_markdown": "<concise answer, 1–3 sentences + 3–7 bullets>",
  "claims": [
    { "text": "<one atomic claim>", "citation_ids": ["<evidence_id>", "..."] }
  ],
  "missing_evidence": false
}"""

ANSWER_USER_TEMPLATE = """QUESTION:
{question}

EVIDENCE_SPANS:
{json_evidence_spans}

Constraints:
- Every claim must include at least one citation_id present in EVIDENCE_SPANS.
- If evidence is insufficient, return:
  {"answer_markdown":"No evidence found for this question in the provided sources.","claims":[],"missing_evidence":true}"""

def _snippet(text: str) -> str:
    """Legacy snippet function for fallback."""
    t = " ".join(text.split())
    return t[:MAX_CITATION_SNIPPET_CHARS] + ("…" if len(t) > MAX_CITATION_SNIPPET_CHARS else "")

def _prepare_evidence_spans_for_llm(evidence: List[Dict], max_spans: int = 8) -> List[Dict[str, Any]]:
    """Convert evidence chunks to LLM-compatible evidence spans."""
    evidence_spans = []
    
    for i, ev in enumerate(evidence[:max_spans]):
        evidence_spans.append({
            "id": f"e{i+1}",
            "text": ev.get('text', ''),
            "section_path": ev.get('section_path', 'Document'),
            "page": ev.get('page_start', 1),
            "chunk_id": ev.get('chunk_id', '')
        })
    
    return evidence_spans

async def _call_ollama_answer(question: str, evidence_spans: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Call Ollama for answer synthesis."""
    if not HTTPX_AVAILABLE:
        log.warning("httpx not available for LLM answer generation")
        return None
    
    try:
        user_message = ANSWER_USER_TEMPLATE.format(
            question=question,
            json_evidence_spans=json.dumps(evidence_spans, indent=2)
        )
        
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": f"{ANSWER_SYSTEM_PROMPT}\n\n{user_message}",
            "stream": False,
            "options": {
                "temperature": 0.0,  # Deterministic for compliance
                "top_p": 0.9,
                "max_tokens": 800
            }
        }
        
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
        
        # Extract and parse JSON response
        response_text = data.get("response", "")
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        
        if json_start >= 0 and json_end > json_start:
            answer_data = json.loads(response_text[json_start:json_end])
            return answer_data
        else:
            log.warning("No valid JSON found in LLM answer response")
            return None
            
    except Exception as e:
        log.error(f"LLM answer generation failed: {e}")
        return None

def _validate_citations(answer_data: Dict[str, Any], evidence_spans: List[Dict[str, Any]]) -> bool:
    """Validate that all citation_ids in answer exist in evidence."""
    if not answer_data.get("claims"):
        return True
    
    evidence_ids = {span["id"] for span in evidence_spans}
    
    for claim in answer_data.get("claims", []):
        for citation_id in claim.get("citation_ids", []):
            if citation_id not in evidence_ids:
                log.warning(f"Invalid citation_id in answer: {citation_id}")
                return False
    
    return True

def _create_citations_from_claims(answer_data: Dict[str, Any], evidence_spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create citation objects from answer claims."""
    citations = []
    evidence_map = {span["id"]: span for span in evidence_spans}
    
    # Collect unique citation IDs from all claims
    citation_ids = set()
    for claim in answer_data.get("claims", []):
        citation_ids.update(claim.get("citation_ids", []))
    
    # Create citation objects
    for citation_id in citation_ids:
        if citation_id in evidence_map:
            span = evidence_map[citation_id]
            citations.append({
                "chunk_id": span["chunk_id"],
                "section_path": span["section_path"],
                "page_span": [span["page"], span["page"]],
                "text": span["text"]
            })
    
    return citations

def _fallback_extractive_answer(evidence: List[Dict]) -> Dict:
    """Fallback extractive answer when LLM fails."""
    if not evidence:
        return {
            "answer": "No evidence found in the specified corpus and filters.",
            "citations": []
        }

    # Simple extractive approach: take top N passages as bullet points
    bullets = []
    citations = []
    for ev in evidence[:5]:
        bullets.append(f"- {_snippet(ev['text'])}")
        citations.append({
            "chunk_id": ev["chunk_id"],
            "section_path": ev.get("section_path") or "",
            "page_span": [ev.get("page_start") or 0, ev.get("page_end") or 0]
        })

    answer = "Here are the most relevant cited passages:\n" + "\n".join(bullets)
    if NO_CITATION_NO_CLAIM and not citations:
        answer = "No evidence found in the specified corpus and filters."

    return {"answer": answer, "citations": citations}

async def compose_answer_llm(evidence: List[Dict], question: str, retrieval_metrics: Dict[str, Any], provider: str = "ollama") -> Dict:
    """Enhanced answer composition with LLM synthesis."""
    with tr.start_as_current_span("compose.answer_llm"):
        if not evidence:
            return {
                "answer": "No evidence found in the specified corpus and filters.",
                "citations": [],
                "confidence": 0.0,
                "missing_evidence": True
            }
        
        # Prepare evidence spans for LLM
        evidence_spans = _prepare_evidence_spans_for_llm(evidence)
        
        # Try LLM answer generation
        answer_data = None
        if provider == "ollama" and HTTPX_AVAILABLE:
            answer_data = await _call_ollama_answer(question, evidence_spans)
        
        # Validate LLM response
        if answer_data and isinstance(answer_data, dict) and _validate_citations(answer_data, evidence_spans):
            # Create citations from validated claims
            citations = _create_citations_from_claims(answer_data, evidence_spans)
            
            # Calculate confidence from retrieval metrics
            confidence = min(1.0, retrieval_metrics.get("avg_score", 0.5) + 0.2)
            
            return {
                "answer": answer_data.get("answer_markdown", ""),
                "citations": citations,
                "confidence": confidence,
                "missing_evidence": answer_data.get("missing_evidence", False),
                "method": "llm_synthesis"
            }
        else:
            log.warning("LLM answer generation failed or invalid, using extractive fallback")
            result = _fallback_extractive_answer(evidence)
            result.update({
                "confidence": retrieval_metrics.get("avg_score", 0.3),
                "method": "extractive_fallback"
            })
            return result

# Legacy function for backward compatibility
def compose_answer(evidence: List[Dict]) -> Dict:
    """Legacy extractive answer composition."""
    return _fallback_extractive_answer(evidence)