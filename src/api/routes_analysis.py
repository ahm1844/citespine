# src/api/routes_analysis.py
from __future__ import annotations
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select, insert, update
from datetime import datetime, timezone
import asyncio, json, os
from typing import Optional

from ..api.schemas import AnalysisResult, UploadResponse, Suggestion, AnalysisMode
from ..ingest.document_analyzer import analyze_document_content
from ..db.session import get_session
from ..db.models import Document, Chunk, DocumentAnalysis
from ..common.config import SETTINGS
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

router = APIRouter(prefix="/analysis", tags=["analysis"])
log = get_logger("routes_analysis")

# Helper: load document text and chunks
def _load_doc(session, source_id: str):
    doc = session.get(Document, source_id)
    if not doc: 
        raise HTTPException(404, "source_id not found")
    
    # Get chunks for this document
    q = select(Chunk).where(Chunk.source_id == source_id).order_by(Chunk.chunk_id)
    chunks = []
    for row in session.execute(q):
        c = row[0]
        chunks.append({
            "chunk_id": c.chunk_id,
            "text": c.text,
            "section_path": c.section_path,
            "page_start": c.page_start,
            "page_end": c.page_end
        })
    
    full_text = "\n\n".join(ch["text"] for ch in chunks if ch.get("text"))
    return doc, full_text, chunks

@router.get("/{source_id}")
def get_analysis(source_id: str):
    with get_session() as s:
        a = s.get(DocumentAnalysis, source_id)
        if not a:
            # Not ready yet
            return {
                "source_id": source_id,
                "mode": "fast", 
                "ready": False,
                "topics": [],
                "questions": [],
                "overview": None
            }
        
        # Return enhanced response with overview
        return {
            "source_id": source_id,
            "mode": a.mode,
            "mode_used": a.mode_used,
            "lang": a.lang,
            "summary": a.summary,
            "topics": a.topics or [],
            "questions": a.questions or [],
            "overview": a.overview,
            "confidence": a.confidence,
            "ready": True,
            "started_at": a.started_at.isoformat() if a.started_at else None,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None
        }

@router.get("/stream/{source_id}")
async def stream_analysis(source_id: str):
    async def gen():
        # Simple polling inside SSE loop
        while True:
            with get_session() as s:
                a = s.get(DocumentAnalysis, source_id)
                if a:
                    payload = {
                        "ready": True, "summary": a.summary, "topics": a.topics,
                        "questions": a.questions, "confidence": a.confidence
                    }
                    yield f"event: ready\ndata: {json.dumps(payload)}\n\n"
                    break
            yield "event: progress\ndata: {\"stage\":\"analyzing\"}\n\n"
            await asyncio.sleep(1.0)
    return StreamingResponse(gen(), media_type="text/event-stream")

def _persist_analysis(s, source_id: str, result):
    """Persist analysis result to database (accepts dict or AnalysisResult)."""
    exists = s.get(DocumentAnalysis, source_id)
    
    # Handle both dict and AnalysisResult objects
    if hasattr(result, 'model_dump'):
        result_dict = result.model_dump()
    else:
        result_dict = result
    
    payload = {
        "mode": result_dict.get("mode", "fast"),
        "mode_used": result_dict.get("mode_used"),
        "lang": result_dict.get("lang"),
        "summary": result_dict.get("summary"),
        "topics": result_dict.get("topics", []),
        "questions": result_dict.get("questions", []),
        "overview": result_dict.get("overview"),
        "confidence": result_dict.get("confidence"),
        "started_at": result_dict.get("started_at"),
        "completed_at": result_dict.get("completed_at")
    }
    
    # Convert questions to proper format if they're AnalysisResult objects
    if "questions" in payload and payload["questions"]:
        questions = payload["questions"]
        if questions and hasattr(questions[0], 'model_dump'):
            payload["questions"] = [q.model_dump() for q in questions]
    
    if exists:
        s.execute(update(DocumentAnalysis).where(DocumentAnalysis.source_id==source_id).values(**payload))
    else:
        s.execute(insert(DocumentAnalysis).values(source_id=source_id, **payload))
    s.commit()

async def _run_analysis(source_id: str, mode: Optional[AnalysisMode] = None):
    """Background task to run document analysis"""
    with TR.start_as_current_span("analysis.run") as sp:
        sp.set_attribute("source_id", source_id)
        sp.set_attribute("mode", mode or "fast")
        log.info("analysis.run.start source_id=%s mode=%s", source_id, mode or "fast")
        
        try:
            with get_session() as s:
                doc, full_text, chunks = _load_doc(s, source_id)     # raise early if missing
                log.info("analysis.run.loaded_doc source_id=%s chunks=%d text_chars=%d", 
                        source_id, len(chunks), len(full_text))
                
                result = await analyze_document_content(source_id, full_text, chunks, mode=mode, lang_hint="en")
                log.info("analysis.run.content_analyzed source_id=%s questions=%d confidence=%s", 
                        source_id, len(result.questions), result.confidence)
                
                _persist_analysis(s, source_id, result)               # must COMMIT inside
                log.info("analysis.run.done source_id=%s ready=%s questions=%d",
                        source_id, True, len(result.questions or []))
                        
        except Exception as e:
            log.error("analysis.run.failed source_id=%s error=%s", source_id, str(e))
            # Also log the full traceback for debugging
            import traceback
            log.error(f"Full traceback: {traceback.format_exc()}")
            # Store failed analysis with proper commit
            try:
                with get_session() as s:
                    failed_result = AnalysisResult(
                        source_id=source_id, 
                        mode=mode or "fast", 
                        ready=True, 
                        confidence=0.0,
                        started_at=datetime.now(timezone.utc),
                        completed_at=datetime.now(timezone.utc)
                    )
                    _persist_analysis(s, source_id, failed_result)
                    log.info("analysis.run.failed_persisted source_id=%s", source_id)
            except Exception as pe:
                log.error("analysis.run.persist_failed source_id=%s error=%s", source_id, str(pe))
