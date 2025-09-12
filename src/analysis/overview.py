"""Document overview generation with LLM synthesis and evidence validation."""
import re
import json
import os
from typing import Dict, List, Any, Optional
from ..common.logging import get_logger
from ..api.schemas import AnalysisMode

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

log = get_logger("analysis/overview")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Prompt B - Document Overview (LLM)
OVERVIEW_SYSTEM_PROMPT = """You analyze regulatory/audit documents. Produce a brief overview (120–180 words) plus structured fields.
Use ONLY the EVIDENCE_SPANS. No citation → no claim. Output STRICT JSON.

Schema:
{
  "overview_markdown": "<120–180 words>",
  "purpose": {"text":"...", "citation_ids":["e1"]},
  "scope": {"text":"...", "citation_ids":["e2"]},
  "key_requirements": [ {"text":"...", "citation_ids":["e7","e9"]} ],
  "effective_dates": [ {"text":"...", "citation_ids":["e4"]} ],
  "amendments": [ {"text":"...", "citation_ids":["e11"]} ],
  "affected_parties": {"text":"...", "citation_ids":["e12"] }
}"""

OVERVIEW_USER_TEMPLATE = """EVIDENCE_SPANS:
{json_overview_spans}

Constraints:
- Each field must list at least one citation_id.
- Keep language precise and neutral."""

def _select_overview_spans(chunks: List[Dict[str, Any]], max_spans: int = 10) -> List[Dict[str, Any]]:
    """Select top spans for overview generation based on structure + anchors."""
    
    # Priority terms for regulatory documents
    anchor_terms = ["shall", "must", "required", "effective on", "beginning on or after", 
                   "purpose", "scope", "applies to", "definitions", "requirements"]
    
    # Score chunks by anchor density and position
    scored_chunks = []
    for i, chunk in enumerate(chunks):
        text = chunk.get('text', '').lower()
        
        # Count anchor terms
        anchor_count = sum(term in text for term in anchor_terms)
        
        # Boost early chunks (likely to contain overview content)
        position_bonus = max(0, 1.0 - (i / len(chunks)))
        
        # Boost chunks with regulatory language
        regulatory_score = len(re.findall(r'\b(shall|must|required|mandate|prohibit)\b', text))
        
        total_score = anchor_count + position_bonus + (regulatory_score * 0.5)
        scored_chunks.append((total_score, chunk))
    
    # Sort by score and take top spans
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    selected = [chunk for score, chunk in scored_chunks[:max_spans]]
    
    return selected

def _prepare_evidence_spans(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Prepare evidence spans for LLM with required ID mapping."""
    evidence_spans = []
    
    for i, chunk in enumerate(chunks):
        evidence_spans.append({
            "id": f"e{i+1}",
            "text": chunk.get('text', ''),
            "section_path": chunk.get('section_path', 'Document'),
            "page": chunk.get('page_start', 1),
            "chunk_id": chunk.get('chunk_id', '')
        })
    
    return evidence_spans

async def _call_ollama_overview(evidence_spans: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Call Ollama for document overview generation."""
    if not HTTPX_AVAILABLE:
        log.warning("httpx not available for LLM overview generation")
        return None
    
    try:
        user_message = OVERVIEW_USER_TEMPLATE.format(
            json_overview_spans=json.dumps(evidence_spans, indent=2)
        )
        
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": f"{OVERVIEW_SYSTEM_PROMPT}\n\n{user_message}",
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "max_tokens": 1500
            }
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
        
        # Extract JSON from response
        response_text = data.get("response", "")
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        
        if json_start >= 0 and json_end > json_start:
            overview_data = json.loads(response_text[json_start:json_end])
            return overview_data
        else:
            log.warning("No valid JSON found in LLM response")
            return None
            
    except Exception as e:
        log.error(f"Ollama overview generation failed: {e}")
        return None

def _create_overview_citations(evidence_spans: List[Dict[str, Any]], overview_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Create citation objects for overview sections."""
    citations = []
    citation_id_to_span = {span["id"]: span for span in evidence_spans}
    
    # Collect all citation_ids from overview sections
    all_citation_ids = set()
    for section_name in ["purpose", "scope", "key_requirements", "effective_dates", "amendments", "affected_parties"]:
        section_data = overview_data.get(section_name, {})
        if isinstance(section_data, list):
            for item in section_data:
                all_citation_ids.update(item.get("citation_ids", []))
        else:
            all_citation_ids.update(section_data.get("citation_ids", []))
    
    # Create citation objects
    for citation_id in all_citation_ids:
        if citation_id in citation_id_to_span:
            span = citation_id_to_span[citation_id]
            citations.append({
                "id": citation_id,
                "chunk_id": span["chunk_id"],
                "page": span["page"],
                "section_path": span["section_path"],
                "evidence_type": "requirement",  # Can be enhanced with type detection
                "score": 0.85,  # Default score
                "highlights": _find_highlights(span["text"], ["shall", "must", "required", "effective"]),
                "text": span["text"]  # <-- needed for frontend highlight rendering
            })
    
    return citations

def _find_highlights(text: str, terms: List[str]) -> List[Dict[str, int]]:
    """Find highlight positions for terms in text."""
    highlights = []
    text_lower = text.lower()
    
    for term in terms:
        term_lower = term.lower()
        start = 0
        while True:
            pos = text_lower.find(term_lower, start)
            if pos == -1:
                break
            highlights.append({"start": pos, "end": pos + len(term)})
            start = pos + 1
    
    # Sort by start position and merge overlapping highlights
    highlights.sort(key=lambda x: x["start"])
    merged = []
    for h in highlights:
        if merged and h["start"] <= merged[-1]["end"]:
            merged[-1]["end"] = max(merged[-1]["end"], h["end"])
        else:
            merged.append(h)
    
    return merged

def _create_fallback_overview(chunks: List[Dict[str, Any]], evidence_spans: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create fallback overview when LLM fails."""
    
    # Extract key information deterministically
    purpose_text = "Document analysis and compliance requirements."
    scope_text = "Regulatory guidance and implementation requirements."
    
    # Find chunks with requirements
    requirement_chunks = []
    for span in evidence_spans[:3]:
        text = span["text"]
        if any(term in text.lower() for term in ["shall", "must", "required"]):
            requirement_chunks.append({
                "text": text[:200] + "..." if len(text) > 200 else text,
                "citation_ids": [span["id"]]
            })
    
    # Find effective dates
    effective_dates = []
    for span in evidence_spans:
        text = span["text"]
        if "effective" in text.lower() and any(term in text.lower() for term in ["date", "on", "after"]):
            effective_dates.append({
                "text": text[:150] + "..." if len(text) > 150 else text,
                "citation_ids": [span["id"]]
            })
            break
    
    overview = {
        "overview_markdown": f"This document contains regulatory requirements and compliance guidance. Key areas include implementation requirements, effective dates, and affected parties.",
        "purpose": {"text": purpose_text, "citation_ids": [evidence_spans[0]["id"]] if evidence_spans else []},
        "scope": {"text": scope_text, "citation_ids": [evidence_spans[1]["id"]] if len(evidence_spans) > 1 else []},
        "key_requirements": requirement_chunks[:3],
        "effective_dates": effective_dates[:2],
        "amendments": [],
        "affected_parties": {"text": "Regulatory entities and compliance professionals.", "citation_ids": []}
    }
    
    return overview

async def build_overview(source_id: str, chunks: List[Dict[str, Any]], mode: AnalysisMode = "fast") -> Dict[str, Any]:
    """Build document overview with citations."""
    
    # Select best spans for overview
    selected_chunks = _select_overview_spans(chunks, max_spans=15 if mode == "deep" else 10)
    evidence_spans = _prepare_evidence_spans(selected_chunks)
    
    overview_data = None
    mode_used = mode
    
    # Try LLM generation for smart/deep modes
    if mode in ["smart", "deep"] and HTTPX_AVAILABLE:
        try:
            overview_data = await _call_ollama_overview(evidence_spans)
            if not overview_data:
                raise Exception("LLM returned empty result")
        except Exception as e:
            log.warning(f"LLM overview generation failed, falling back: {e}")
            mode_used = "fast(fallback)"
    
    # Fallback to deterministic overview
    if not overview_data:
        overview_data = _create_fallback_overview(selected_chunks, evidence_spans)
        if mode == "fast":
            mode_used = "fast"
        else:
            mode_used = f"{mode}(fallback)"
    
    # Create citations for the overview
    citations = _create_overview_citations(evidence_spans, overview_data)
    
    # Add citations to overview data
    overview_data["citations"] = citations
    
    log.info(f"Built overview for {source_id}: mode_used={mode_used}, citations={len(citations)}")
    
    return {
        "overview": overview_data,
        "mode_used": mode_used
    }
