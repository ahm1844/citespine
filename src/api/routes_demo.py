from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import io, os, csv, json, tempfile

from ..common.config import SETTINGS
from .guards import demo_rate_limit

# Use internal ingest & retrieval/compose modules
from ..ingest.runner import ingest_single_pdf   # Modified to accept BytesIO + metadata kwargs
from ..retrieval.router import retrieve_any     # Uses session, query_text, filters, top_k, probes
from ..answer.compose import compose_answer     # Takes evidence List[Dict] -> Dict
from ..db.session import get_session

router = APIRouter()

def _now_utc(): return datetime.now(timezone.utc)

def _assert_demo_enabled():
    if not SETTINGS.DEMO_MODE:
        raise HTTPException(404, "Demo disabled")

class Filters(BaseModel):
    framework: Optional[str] = None
    jurisdiction: Optional[str] = None
    doc_type: Optional[str] = None
    authority_level: Optional[str] = None
    as_of: Optional[str] = None

def ingest_single_pdf_bytesio(file_content: bytes, filename: str, namespace: str = "default", extra_meta: Dict = None) -> list:
    """Wrapper to handle BytesIO input for demo uploads."""
    # Create temporary file from bytes
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(file_content)
        tmp_path = tmp_file.name
    
    try:
        # Default metadata for demo uploads
        metadata = {
            "title": filename or "Demo Upload",
            "doc_type": "standard",
            "framework": "Other", 
            "jurisdiction": "US",
            "authority_level": "authoritative",
            "effective_date": "2024-01-01",
            "version": "1.0"
        }
        
        # Update with any extra metadata
        if extra_meta:
            metadata.update(extra_meta)
        
        # Call existing ingest function
        result = ingest_single_pdf(tmp_path, metadata)
        
        if result.get("accepted"):
            # Return a list of document IDs for compatibility
            return [result["source_id"]]
        else:
            raise Exception(f"Ingest failed: {result.get('errors', 'Unknown error')}")
    
    finally:
        # Clean up temporary file
        try:
            os.unlink(tmp_path)
        except:
            pass

@router.post("/query")
async def demo_query(
    response: Response,
    file: UploadFile = File(...),
    q: Optional[str] = Form("", description="Optional question; leave blank to rely on document content"),
    filters: str = Form("{}"),
    rate_guard: None = Depends(demo_rate_limit(SETTINGS.DEMO_RATE_LIMIT_PER_IP))
) -> Dict[str, Any]:
    _assert_demo_enabled()

    contents = await file.read()
    if len(contents) > SETTINGS.DEMO_MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(413, "File too large")
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(415, "Only PDF supported in demo")

    expires_at = _now_utc() + timedelta(minutes=SETTINGS.DEMO_DELETE_AFTER_MIN)
    try:
        doc_ids = ingest_single_pdf_bytesio(
            contents,
            filename=file.filename,
            namespace=SETTINGS.DEMO_NAMESPACE,
            extra_meta={"demo": True, "expires_at": expires_at.isoformat()}
        )
    except Exception as e:
        raise HTTPException(400, f"Ingest failed: {e}")

    try:
        f = Filters.model_validate_json(filters)  # if 'filters' is JSON string
    except Exception:
        try:
            f = Filters(**json.loads(filters))
        except:
            f = Filters()  # fallback to empty filters

    # Retrieve with filters first, then vector similarity
    session = get_session()
    try:
        # retrieve_any signature: (session, query_text, filters, top_k, probes)
        retrieval = retrieve_any(
            session,
            q or "What are the key requirements and provisions?",  # default question if none provided
            f.model_dump(exclude_none=True),
            top_k=10, 
            probes=15
        )
        # compose_answer signature: (evidence) -> Dict
        ans = compose_answer(retrieval)   
    except Exception as e:
        raise HTTPException(500, f"Query failed: {e}")
    finally:
        session.close()

    return {
        "answer": ans.get("answer", ""),
        "citations": ans.get("citations", []),
        "structured": ans.get("structured", {}),
        "metrics": ans.get("metrics", {})
    }

class ExportReq(BaseModel):
    format: str
    email: Optional[EmailStr] = None
    consent: Optional[bool] = False
    memo: Dict[str, Any]

@router.post("/export")
async def demo_export(req: ExportReq):
    _assert_demo_enabled()
    if SETTINGS.DEMO_EXPORT_REQUIRE_EMAIL and (not req.email or not req.consent):
        raise HTTPException(400, "Email & consent required for export")

    os.makedirs("data", exist_ok=True)
    leads = "data/leads.csv"
    new = not os.path.exists(leads)
    with open(leads, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new: w.writerow(["ts","email","source","consent"])
        w.writerow([_now_utc().isoformat(), req.email or "", "demo_export", bool(req.consent)])

    from fastapi.responses import JSONResponse
    return JSONResponse(req.memo, media_type="application/json",
                        headers={"Content-Disposition": 'attachment; filename="memo.json"'})

@router.get("/metrics")
async def demo_metrics():
    # Optionally surface perf summary if available
    try:
        perf = json.load(open("data/eval/perf_load.json","r",encoding="utf-8"))
        perf = perf.get("summary", {})
    except Exception:
        perf = {}
    return {"ok": True, "perf_summary": perf}
