import React, { useState } from "react";

type Filters = { framework?: string; jurisdiction?: string; doc_type?: string;
  authority_level?: string; as_of?: string; };

export default function DemoPane() {
  const [file, setFile] = useState<File|null>(null);
  const [filters, setFilters] = useState<Filters>({});
  const [q, setQ] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [email, setEmail] = useState("");
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState<string|null>(null);

  async function runDemo() {
    setError(null); setLoading(true); setResult(null);
    if (!file) { setError("Please choose a PDF"); setLoading(false); return; }
    const form = new FormData();
    form.append("file", file);
    form.append("q", q);
    form.append("filters", JSON.stringify(filters));
    const res = await fetch("/demo/query", { method: "POST", body: form });
    if (!res.ok) { setError(`Query failed (${res.status})`); setLoading(false); return; }
    const json = await res.json(); setResult(json); setLoading(false);
  }

  async function exportMemo() {
    const memo = result?.structured?.memo;
    if (!memo) { setError("No memo to export"); return; }
    const res = await fetch("/demo/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format: "json", email, consent, memo })
    });
    if (!res.ok) { setError(`Export failed (${res.status})`); return; }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "memo.json"; a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div style={{maxWidth:900, margin:"0 auto", padding:"1rem"}}>
      <h2>Try CiteSpine (Demo)</h2>
      <p>Upload a PDF → choose filters → get a cited answer → export memo.</p>

      <div style={{margin:"12px 0"}}>
        <input type="file" accept="application/pdf" onChange={e=>setFile(e.target.files?.[0]||null)} />
      </div>

      <input placeholder="Optional question (e.g., 'What are ESEF primary tagging requirements?')"
             value={q} onChange={e=>setQ(e.target.value)} style={{width:"100%",margin:"8px 0"}} />

      <div style={{display:"grid",gridTemplateColumns:"repeat(2,1fr)",gap:"8px",margin:"8px 0"}}>
        <input placeholder="framework (e.g., IFRS)" onChange={e=>setFilters(f=>({...f, framework: e.target.value||undefined}))}/>
        <input placeholder="jurisdiction (e.g., EU)" onChange={e=>setFilters(f=>({...f, jurisdiction: e.target.value||undefined}))}/>
        <input placeholder="doc_type (e.g., standard)" onChange={e=>setFilters(f=>({...f, doc_type: e.target.value||undefined}))}/>
        <input placeholder="authority_level (e.g., authoritative)" onChange={e=>setFilters(f=>({...f, authority_level: e.target.value||undefined}))}/>
        <input placeholder="as_of (YYYY-MM-DD)" onChange={e=>setFilters(f=>({...f, as_of: e.target.value||undefined}))}/>
      </div>

      <button onClick={runDemo} disabled={loading}>{loading ? "Running…" : "Run"}</button>
      {error && <div style={{color:"red",marginTop:8}}>{error}</div>}

      {result && (
        <div style={{marginTop:16}}>
          <h3>Answer</h3>
          <pre style={{whiteSpace:"pre-wrap"}}>{result.answer || "(empty)"}</pre>
          <h4>Citations</h4>
          <ul>
            {(result.citations||[]).map((c:any,i:number)=>
              <li key={i}>{c.doc_id ?? "(doc)"} — {c.page_span ?? ""}</li>
            )}
          </ul>

          <h4>Export Memo</h4>
          <input placeholder="you@company.com" value={email}
                 onChange={e=>setEmail(e.target.value)} />
          <label style={{marginLeft:8}}>
            <input type="checkbox" checked={consent}
                   onChange={e=>setConsent(e.target.checked)} />
            I consent to be contacted about this demo
          </label>
          <div>
            <button onClick={exportMemo} style={{marginTop:8}}>Export JSON</button>
          </div>

          <h4>Runtime Metrics</h4>
          <pre>{JSON.stringify(result.metrics||{}, null, 2)}</pre>
          <p style={{marginTop:8}}>
            Watch a 3‑minute demo: <a href="/site/demo.mp4" target="_blank" rel="noreferrer">Open</a>
          </p>
        </div>
      )}
    </div>
  );
}
