# src/api/routes_query.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
import time
import os
from typing import List, Dict, Any

from .schemas import QueryReq, QueryResp, EvidenceSegment
from ..db.session import get_session
from ..retrieval.router import retrieve_any
# legacy compose_answer not used; remove to avoid confusion
from ..common.logging import get_logger

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

router = APIRouter(tags=["query"])
log = get_logger("routes_query")

def _find_highlights(text: str, boost_terms: List[str]) -> List[Dict[str, int]]:
    """Find highlight positions for boost terms in text"""
    highlights = []
    text_lower = text.lower()
    
    for term in boost_terms:
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

def _boost_by_terms(chunks: List[Dict[str, Any]], boost_terms: List[str]) -> List[Dict[str, Any]]:
    """Re-rank chunks by boosting those containing boost terms"""
    boosted = []
    
    for chunk in chunks:
        boost_score = 0
        text_lower = chunk.get("text", "").lower()
        
        for term in boost_terms:
            boost_score += text_lower.count(term.lower())
        
        # Apply boost to existing score
        original_score = chunk.get("distance", 1.0)  # Lower distance = better
        if boost_score > 0:
            # Reduce distance (improve ranking) for chunks with boost terms
            chunk["distance"] = original_score * (0.5 ** boost_score)
        
        boosted.append(chunk)
    
    # Re-sort by distance (lower is better)
    return sorted(boosted, key=lambda x: x.get("distance", 1.0))

@router.post("/query", response_model=QueryResp)
async def enhanced_query(req: QueryReq):
    """Enhanced query endpoint with support for executable suggestions"""
    with TR.start_as_current_span("query") as sp:
        sp.set_attribute("top_k", req.top_k)
        sp.set_attribute("probes", req.probes)
        sp.set_attribute("focus_source_id", req.focus_source_id or "")
        sp.set_attribute("expected_evidence_type", req.expected_evidence_type or "")
        
        session = get_session()
        t0 = time.perf_counter()
        
        try:
            # Apply filters - if focus_source_id is provided, add it to filters
            filters = dict(req.filters or {})
            if req.focus_source_id:
                # This would need to be handled in retrieve_any to filter by source_id
                # For now, we'll pass it as a special filter
                filters["_focus_source_id"] = req.focus_source_id
            
            # Retrieve with filters
            hits = retrieve_any(session, req.q, filters, req.top_k, probes=req.probes)
            
            # Apply boost terms if provided
            if req.boost_terms:
                hits = _boost_by_terms(hits, req.boost_terms)
            
            latency_ms = int((time.perf_counter() - t0) * 1000)
            
            # Build evidence segments with highlights
            evidence_segments: List[EvidenceSegment] = []
            for ch in hits[:5]:
                highlights = _find_highlights(ch.get("text", ""), req.boost_terms or [])
                evidence_segments.append(EvidenceSegment(
                    chunk_id=ch["chunk_id"],
                    page=ch.get("page_start"), 
                    section=ch.get("section_path"),
                    text=ch.get("text", "")[:1000],  # Truncate for response size
                    highlights=highlights,
                    relevance=1.0 - min(ch.get("distance", 0.5), 1.0),  # Convert distance to relevance
                    type=req.expected_evidence_type or None
                ))
            
            # Use enhanced LLM answer composition
            from ..answer.compose import compose_answer_llm
            
            # Calculate retrieval metrics for confidence scoring
            retrieval_metrics = {
                "avg_score": sum(1.0 - min(h.get("distance", 0.5), 1.0) for h in hits[:5]) / max(len(hits[:5]), 1),
                "chunks_retrieved": len(hits),
                "latency_ms": latency_ms
            }
            
            # Generate LLM-powered answer
            answer_result = await compose_answer_llm(
                hits, req.q, retrieval_metrics, provider=os.getenv("LLM_PROVIDER", "ollama")
            )
            
            return QueryResp(
                answer=answer_result.get("answer", ""),
                citations=answer_result.get("citations", []),
                evidence_segments=evidence_segments,
                metrics={
                    "latency_ms": latency_ms,
                    "chunks_retrieved": len(hits),
                    "evidence_segments": len(evidence_segments),
                    "confidence": answer_result.get("confidence", 0.0),
                    "method": answer_result.get("method", "unknown"),
                    "missing_evidence": answer_result.get("missing_evidence", False)
                }
            )
            
        except Exception as e:
            log.error(f"Query failed: {e}")
            raise HTTPException(500, f"Query failed: {str(e)}")
        finally:
            session.close()
