from fastapi import FastAPI, Body, Depends, UploadFile, File, Form, Response, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, EmailStr
from typing import Dict, Any, List, Optional
import time, csv, shutil
from pathlib import Path
from datetime import datetime, timezone
import asyncio
from opentelemetry.trace import get_current_span
from ..common.logging import get_logger
from ..common.progress import log_progress

def set_trace_header(resp: Response):
    span = get_current_span()
    ctx = span.get_span_context()
    resp.headers["X-Trace-Id"] = format(ctx.trace_id, "032x")
from ..common.constants import EXCEPTIONS_CSV, PROCESSED_DIR
from ..common.config import SETTINGS
from ..db.session import get_session
from ..answer.compose import compose_answer
from ..retrieval.router import retrieve_any
from ..ingest.runner import run_ingest, ingest_single_pdf
from ..obs.manifest import write_manifest
from ..artifacts.memo import build_memo
from .auth import require_invite, set_invite_cookie, require_api_key

log = get_logger("api")

app = FastAPI(title="CiteSpine API", version="0.1.0")

# Serve public landing page and built React app
app.mount("/site", StaticFiles(directory="public", html=True), name="site")
app.mount("/app", StaticFiles(directory="frontend/dist", html=True), name="app")

# Demo routes (if enabled)
if SETTINGS.DEMO_MODE:
    from .routes_demo import router as demo_router
    app.include_router(demo_router, prefix="/demo", tags=["demo"])

    # TTL cleanup for demo documents
    async def purge_expired_demo_docs():
        # TODO: Implement: delete from DB where namespace=SETTINGS.DEMO_NAMESPACE and expires_at < now
        # If you have ORM models, write the query here. For now, leave as TODO/log.
        pass

    @app.on_event("startup")
    async def _start_demo_gc():
        async def loop():
            while True:
                try:
                    await purge_expired_demo_docs()
                except Exception:
                    pass
                await asyncio.sleep(300)  # every 5 minutes
        asyncio.create_task(loop())

# Authentication routes
@app.get("/auth/invite")
def auth_invite(token: str, response: Response):
    return set_invite_cookie(token, response)

# Lead capture for public site
LEADS_CSV = Path("data/leads.csv"); LEADS_CSV.parent.mkdir(parents=True, exist_ok=True)

class Lead(BaseModel):
    name: str
    email: EmailStr
    company: str | None = None
    message: str | None = None

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/public/lead")
def public_lead(lead: Lead, request: Request):
    new = not LEADS_CSV.exists()
    with LEADS_CSV.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new: w.writerow(["ts","name","email","company","message","ip"])
        w.writerow([datetime.utcnow().isoformat(), lead.name, lead.email, lead.company or "", lead.message or "", request.client.host if request.client else ""])
    return {"ok": True}

# Suggestions for first-time users (invite-gated)
DEFAULT_SUGGESTIONS = [
    "What does PCAOB require for ICFR audits?",
    "What are ESEF inline XBRL tagging requirements?",
    "Show disclosure guidance for revenue recognition.",
]

@app.get("/suggestions", dependencies=[Depends(require_invite)])
def suggestions():
    return {"suggestions": DEFAULT_SUGGESTIONS}

# Upload single PDF
@app.post("/upload", dependencies=[Depends(require_invite)])
async def upload_pdf(
    file: UploadFile = File(...),
    framework: Optional[str] = Form(None),
    jurisdiction: Optional[str] = Form(None),
    doc_type: Optional[str] = Form(None),
    authority_level: Optional[str] = Form(None),
    effective_date: Optional[str] = Form(None),
    version: Optional[str] = Form(None),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF supported")
    Path(SETTINGS.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    dest = Path(SETTINGS.UPLOAD_DIR) / file.filename
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    meta = {
        "title": file.filename,
        "framework": framework,
        "jurisdiction": jurisdiction,
        "doc_type": doc_type,
        "authority_level": authority_level,
        "effective_date": effective_date,
        "version": version,
    }
    return ingest_single_pdf(str(dest), meta)

class QueryFilters(BaseModel):
    framework: str | None = None
    jurisdiction: str | None = None
    doc_type: str | None = None
    authority_level: str | None = None
    as_of: str | None = None

class QueryRequest(BaseModel):
    q: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    top_k: Optional[int] = 10
    probes: Optional[int] = 15

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

# UI query (invite)
@app.post("/query", dependencies=[Depends(require_invite)])
def ui_query(req: QueryRequest):
    session = get_session()
    t0 = time.perf_counter()
    hits = retrieve_any(session, req.q, req.filters, req.top_k, probes=req.probes or 10)
    latency_ms = int((time.perf_counter() - t0) * 1000)
    out = compose_answer(hits)
    manifest_path = write_manifest("query", {
        "q": req.q,
        "filters": req.filters,
        "top_k": req.top_k,
        "probes": req.probes or 10,
        "backend": SETTINGS.VECTOR_BACKEND,
        "latency_ms": latency_ms,
        "citations": [c["chunk_id"] for c in out.get("citations", [])]
    })
    return {**out, "run_manifest": manifest_path, "latency_ms": latency_ms, "backend": SETTINGS.VECTOR_BACKEND}

# Programmatic query (API key)
@app.post("/v1/query", dependencies=[Depends(require_api_key)])
def api_query_v1(req: QueryRequest):
    session = get_session()
    t0 = time.perf_counter()
    hits = retrieve_any(session, req.q, req.filters, req.top_k, probes=req.probes or 10)
    latency_ms = int((time.perf_counter() - t0) * 1000)
    out = compose_answer(hits)
    manifest_path = write_manifest("query", {
        "q": req.q,
        "filters": req.filters,
        "top_k": req.top_k,
        "probes": req.probes or 10,
        "backend": SETTINGS.VECTOR_BACKEND,
        "latency_ms": latency_ms,
        "citations": [c["chunk_id"] for c in out.get("citations", [])]
    })
    return {**out, "run_manifest": manifest_path, "latency_ms": latency_ms, "backend": SETTINGS.VECTOR_BACKEND}

@app.post("/generate/{artifact}", dependencies=[Depends(require_invite)])
def api_generate(artifact: str, req: QueryRequest):
    session = get_session()
    ev = retrieve_any(session, req.q, req.filters, req.top_k, probes=req.probes or 10)
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
        "filters": req.filters,
        "backend": SETTINGS.VECTOR_BACKEND,
        "references": artifact_json.get("references", [])
    })
    return {"artifact": artifact_json, "run_manifest": manifest_path, "backend": SETTINGS.VECTOR_BACKEND}

@app.get("/eval/report")
def api_eval_report():
    # Placeholder until Step 10 implements evaluation harness
    return {"status": "not_run_yet", "message": "Run `make eval` after Step 10 to populate results."}

@app.get("/demo", response_class=HTMLResponse, dependencies=[Depends(require_invite)])
def demo_page():
    # Simple, dependency-free UI for live demo.
    return """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>CiteSpine Demo</title>
<style>
  body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 2rem; max-width: 900px; }
  .row { display: flex; gap: 1rem; flex-wrap: wrap; margin: .5rem 0; }
  label { font-weight: 600; }
  input, select, button, textarea { font-size: 1rem; padding: .5rem; }
  textarea { width: 100%; height: 120px; }
  pre { background: #0b1021; color: #cfe3ff; padding: 1rem; border-radius: 8px; overflow: auto; }
  .cit { padding: .5rem; border-left: 3px solid #6ea8fe; background: #f7f9ff; margin: .5rem 0; }
</style>
</head>
<body>
<h1>CiteSpine — Demo</h1>
<p>Ask a question, apply filters, and see grounded answers with citations. <em>in our project with the client, we are gonna use Pinecone... for our project, we will use pgvector.</em></p>
<div class="row">
  <label>Question</label>
  <textarea id="q" placeholder="e.g., What does PCAOB require for ICFR audits?"></textarea>
</div>
<div class="row">
  <div>
    <label>Framework</label>
    <select id="framework">
      <option value="">(any)</option>
      <option>IFRS</option><option>US_GAAP</option><option>Other</option>
    </select>
  </div>
  <div>
    <label>Jurisdiction</label>
    <select id="jurisdiction">
      <option value="">(any)</option>
      <option>US</option><option>EU</option><option>UK</option><option>Global</option><option>Other</option>
    </select>
  </div>
  <div>
    <label>Doc Type</label>
    <select id="doc_type">
      <option value="">(any)</option>
      <option>standard</option><option>filing</option><option>policy</option><option>memo</option><option>disclosure</option>
    </select>
  </div>
  <div>
    <label>Authority</label>
    <select id="authority_level">
      <option value="">(any)</option>
      <option>authoritative</option><option>interpretive</option><option>internal_policy</option>
    </select>
  </div>
  <div>
    <label>As-of</label>
    <input id="as_of" type="date" value="2024-12-31"/>
  </div>
  <div>
    <label>Top-K</label>
    <input id="top_k" type="number" min="1" max="50" value="10"/>
  </div>
  <div>
    <label>Probes</label>
    <input id="probes" type="number" min="1" max="200" value="15"/>
  </div>
</div>
<div class="row">
  <button onclick="runQuery()">Query</button>
  <button onclick="genMemo()">Generate Memo</button>
</div>
<h3>Answer</h3>
<pre id="answer">—</pre>
<h3>Citations</h3>
<div id="cits"></div>
<script>
async function runQuery() {
  const payload = buildPayload();
  const res = await fetch('/query', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
  const data = await res.json();
  document.getElementById('answer').textContent = data.answer + "\\n\\nbackend=" + (data.backend||'?') + " latency_ms=" + (data.latency_ms||'?');
  renderCitations(data.citations||[]);
}
async function genMemo() {
  const payload = buildPayload();
  const res = await fetch('/generate/memo', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
  const data = await res.json();
  document.getElementById('answer').textContent = JSON.stringify(data.artifact, null, 2);
  renderCitations((data.artifact && data.artifact._source_map || []).map(m => ({chunk_id:m.chunk_id, page_span:m.page_span, section_path:''})));
}
function buildPayload() {
  const f = (id)=>document.getElementById(id).value.trim();
  const filters = {};
  if (f('framework')) filters.framework = f('framework');
  if (f('jurisdiction')) filters.jurisdiction = f('jurisdiction');
  if (f('doc_type')) filters.doc_type = f('doc_type');
  if (f('authority_level')) filters.authority_level = f('authority_level');
  if (f('as_of')) filters.as_of = f('as_of');
  return { q: f('q'), filters, top_k: parseInt(f('top_k')||'10'), probes: parseInt(f('probes')||'10') };
}
function renderCitations(cits) {
  const root = document.getElementById('cits'); root.innerHTML = '';
  cits.forEach(c => {
    const d = document.createElement('div');
    d.className = 'cit';
    d.textContent = `${c.chunk_id}  pages ${c.page_span ? c.page_span.join('-'):''}  ${c.section_path||''}`;
    root.appendChild(d);
  });
}
</script>
</body></html>
    """
