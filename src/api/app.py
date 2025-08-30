from fastapi import FastAPI, Body
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List
import time
from ..common.logging import get_logger
from ..common.progress import log_progress
from ..common.constants import EXCEPTIONS_CSV, PROCESSED_DIR
from ..common.config import SETTINGS
from ..db.session import get_session
from ..answer.compose import compose_answer
from ..retrieval.router import retrieve_any
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
    t0 = time.perf_counter()
    ev = retrieve_any(session, req.q, req.filters.model_dump(exclude_none=True), req.top_k, probes=req.probes or 10)
    latency_ms = int((time.perf_counter() - t0) * 1000)
    out = compose_answer(ev)
    manifest_path = write_manifest("query", {
        "q": req.q,
        "filters": req.filters.model_dump(exclude_none=True),
        "top_k": req.top_k,
        "probes": req.probes or 10,
        "backend": SETTINGS.VECTOR_BACKEND,
        "latency_ms": latency_ms,
        "citations": [c["chunk_id"] for c in out.get("citations", [])]
    })
    return {**out, "run_manifest": manifest_path, "latency_ms": latency_ms, "backend": SETTINGS.VECTOR_BACKEND}

@app.post("/generate/{artifact}")
def api_generate(artifact: str, req: QueryRequest):
    session = get_session()
    ev = retrieve_any(session, req.q, req.filters.model_dump(exclude_none=True), req.top_k, probes=req.probes or 10)
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
        "backend": SETTINGS.VECTOR_BACKEND,
        "references": artifact_json.get("references", [])
    })
    return {"artifact": artifact_json, "run_manifest": manifest_path, "backend": SETTINGS.VECTOR_BACKEND}

@app.get("/eval/report")
def api_eval_report():
    # Placeholder until Step 10 implements evaluation harness
    return {"status": "not_run_yet", "message": "Run `make eval` after Step 10 to populate results."}

@app.get("/demo", response_class=HTMLResponse)
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
