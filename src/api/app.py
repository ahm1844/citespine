from fastapi import FastAPI, Body
from pydantic import BaseModel, Field
from typing import Dict, Any, List
from ..common.logging import get_logger
from ..common.progress import log_progress
from ..common.constants import EXCEPTIONS_CSV, PROCESSED_DIR
from ..db.session import get_session
from ..answer.compose import compose_answer
from ..retrieval.retriever import retrieve
from ..ingest.runner import run_ingest
from ..obs.manifest import write_manifest
from ..artifacts.memo import build_memo

log = get_logger("api")

app = FastAPI(title="CiteSpine API", version="0.1.0")

class QueryFilters(BaseModel):
    framework: str | None = None
    jurisdiction: str | None = None
    doc_type: str | None = None
    authority_level: str | None = None
    as_of: str | None = None

class QueryRequest(BaseModel):
    q: str = Field(..., min_length=2)
    filters: QueryFilters = Field(default_factory=QueryFilters)
    top_k: int | None = None
    probes: int | None = Field(default=None, ge=1, le=200)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ingest")
def api_ingest(payload: Dict[str, Any] = Body(default=None)):
    log_progress("API_INGEST", "START")
    run_ingest()
    log_progress("API_INGEST", "END")
    return {"status": "ingest_complete", "processed_dir": PROCESSED_DIR}

@app.get("/ingest/exceptions")
def api_exceptions():
    try:
        txt = open(EXCEPTIONS_CSV, "r", encoding="utf-8").read()
        rows = [r for r in txt.splitlines()]
        return {"csv_path": EXCEPTIONS_CSV, "rows": rows[:5000]}
    except FileNotFoundError:
        return {"csv_path": EXCEPTIONS_CSV, "rows": []}

@app.post("/query")
def api_query(req: QueryRequest):
    session = get_session()
    ev = retrieve(session, req.q, req.filters.model_dump(exclude_none=True), req.top_k, probes=req.probes or 10)
    out = compose_answer(ev)
    manifest_path = write_manifest("query", {
        "q": req.q,
        "filters": req.filters.model_dump(exclude_none=True),
        "top_k": req.top_k,
        "citations": [c["chunk_id"] for c in out.get("citations", [])]
    })
    return {**out, "run_manifest": manifest_path}

@app.post("/generate/{artifact}")
def api_generate(artifact: str, req: QueryRequest):
    session = get_session()
    ev = retrieve(session, req.q, req.filters.model_dump(exclude_none=True), req.top_k, probes=req.probes or 10)
    artifact_lower = artifact.lower()
    if artifact_lower == "memo":
        artifact_json = build_memo(ev)
    else:
        # Safe default until dedicated mappers are added
        artifact_json = {
            "artifact_type": artifact,
            "fields": {},
            "_source_map": [{"chunk_id": e["chunk_id"], "page_span": [e.get("page_start") or 0, e.get("page_end") or 0]} for e in ev],
            "_flags": {},
            "references": [e["chunk_id"] for e in ev]
        }
    manifest_path = write_manifest("artifact", {
        "artifact": artifact_lower,
        "q": req.q,
        "filters": req.filters.model_dump(exclude_none=True),
        "references": artifact_json.get("references", [])
    })
    return {"artifact": artifact_json, "run_manifest": manifest_path}

@app.get("/eval/report")
def api_eval_report():
    # Placeholder until Step 10 implements evaluation harness
    return {"status": "not_run_yet", "message": "Run `make eval` after Step 10 to populate results."}
