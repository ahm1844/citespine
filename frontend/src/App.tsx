import React, { useEffect, useState } from "react";
import Header from "./components/Header";
import Footer from "./components/Footer";
import Dropzone from "./components/Dropzone";
import QueryForm from "./components/QueryForm";
import Citations from "./components/Citations";
import History, { pushHistory } from "./components/History";
import Toast, { makeToaster } from "./components/Toast";

type Cite = {
  chunk_id?: string; text?: string; framework?: string; jurisdiction?: string;
  doc_type?: string; authority_level?: string; page_start?: number; page_end?: number; section_path?: string;
};

export default function App() {
  const [about, setAbout] = useState(false);
  const [docsOpen, setDocsOpen] = useState(false);
  const [apiOpen, setApiOpen] = useState(false);
  const [secOpen, setSecOpen] = useState(false);

  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [presetQ, setPresetQ] = useState<string>("");

  const [answer, setAnswer] = useState<string>("-");
  const [cites, setCites] = useState<Cite[]>([]);
  const [loading, setLoading] = useState(false);

  const [toasts, setToasts] = useState<any[]>([]);
  const toast = makeToaster(setToasts);

  useEffect(() => {
    fetch("/suggestions", { credentials: "include" })
      .then(r => r.ok ? r.json() : [])
      .then(d => Array.isArray(d) ? setSuggestions(d) : setSuggestions([]))
      .catch(() => setSuggestions([]));
  }, []);

  async function onAsk(q: string, filters: any, topK: number, probes: number) {
    setLoading(true); setAnswer(""); setCites([]);
    toast("Searching…", "info");
    try {
      const res = await fetch("/query", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ q, filters, top_k: topK, probes })
      });
      const data = await res.json();
      setAnswer(data.answer ?? "No evidence found.");
      setCites(data.citations ?? []);
      pushHistory(q);
      if (data.citations?.length) toast(`Found ${data.citations.length} citation${data.citations.length===1?"":"s"}.`, "ok");
      else toast("No evidence found.", "info");
    } catch {
      setAnswer("Request failed."); toast("Request failed.", "err");
    } finally { setLoading(false); }
  }

  async function onExportMemo(q: string, filters: any, topK: number, probes: number) {
    if (!q.trim()) { toast("Enter a question first.", "info"); return; }
    try {
      const res = await fetch("/generate/memo", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ q, filters, top_k: topK, probes })
      });
      const blob = new Blob([JSON.stringify(await res.json(), null, 2)], { type: "application/json" });
      const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "memo.json"; a.click();
      toast("Memo exported.", "ok");
    } catch { toast("Export failed.", "err"); }
  }

  return (
    <div className="container">
      <Header
        onOpenAbout={() => setAbout(true)}
        onOpenDocs={() => setDocsOpen(true)}
        onOpenApi={() => setApiOpen(true)}
        onOpenSecurity={() => setSecOpen(true)}
      />

      {/* Sheets (modals) */}
      {about && (
        <div className="sheet" role="dialog" aria-modal="true" onClick={()=>setAbout(false)}>
          <div className="sheet-box" onClick={(e)=>e.stopPropagation()}>
            <h3>About this demo</h3>
            <p>This is an invite‑gated preview. Upload a PDF, ask a question, and see citations. We never claim without evidence.</p>
            <div style={{display:"flex",justifyContent:"flex-end"}}><button className="btn" onClick={()=>setAbout(false)}>Close</button></div>
          </div>
        </div>
      )}

      {docsOpen && (
        <div className="sheet" role="dialog" aria-modal="true" onClick={()=>setDocsOpen(false)}>
          <div className="sheet-box" onClick={(e)=>e.stopPropagation()}>
            <h3>Docs</h3>
            <p>See README for setup, API reference, and evaluation. This modal keeps the demo flow in one place.</p>
            <a className="nav-link" href="/site">Open docs page</a>
          </div>
        </div>
      )}

      {apiOpen && (
        <div className="sheet" role="dialog" aria-modal="true" onClick={()=>setApiOpen(false)}>
          <div className="sheet-box" onClick={(e)=>e.stopPropagation()}>
            <h3>API</h3>
            <p>Programmatic access uses <code>X-Api-Key</code> and JSON payloads.</p>
            <pre className="answer" style={{whiteSpace:"pre-wrap"}}>
{`curl -X POST http://localhost:8000/v1/query \\
  -H "X-Api-Key: <your-key>" -H "Content-Type: application/json" \\
  -d '{"q":"What does PCAOB require for ICFR?","filters":{},"top_k":10}'`}
            </pre>
            <div style={{display:"flex",justifyContent:"flex-end"}}><button className="btn" onClick={()=>setApiOpen(false)}>Close</button></div>
          </div>
        </div>
      )}

      {secOpen && (
        <div className="sheet" role="dialog" aria-modal="true" onClick={()=>setSecOpen(false)}>
          <div className="sheet-box" onClick={(e)=>e.stopPropagation()}>
            <h3>Security</h3>
            <p>Local‑first, invite‑gated. Evidence‑only responses. No training on your data. Remove content any time.</p>
            <div style={{display:"flex",justifyContent:"flex-end"}}><button className="btn" onClick={()=>setSecOpen(false)}>Close</button></div>
          </div>
        </div>
      )}

      {/* Upload + Ask */}
      <div className="grid">
        <div className="card">
          <h2>Upload</h2>
          <p className="muted">Drop a PDF here. We'll parse it and make it searchable.</p>
          <Dropzone notify={toast} />
        </div>

        <QueryForm
          preset={presetQ}
          suggestions={suggestions}
          onAsk={onAsk}
          onExportMemo={onExportMemo}
        />
      </div>

      {/* Answer */}
      <div className="card section">
        <h3>Answer</h3>
        {loading
          ? <div className="skel"><div className="skel-line"></div><div className="skel-line"></div><div className="skel-line"></div></div>
          : <div className="answer">{answer || "-"}</div>}
      </div>

      {/* Citations */}
      <div className="card section-sm">
        <h3>Citations</h3>
        {loading ? <div className="skel"><div className="skel-line"></div><div className="skel-line"></div></div>
                 : <Citations items={cites} />}
      </div>

      {/* Recent questions */}
      <div className="card section-sm">
        <History onPick={(q)=> setPresetQ(q)} suggestions={suggestions} />
      </div>

      <Footer />

      <Toast items={toasts} onClose={(id)=> setToasts(list => list.filter((t:any) => t.id !== id))} />
    </div>
  );
}