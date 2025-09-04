import React, { useEffect, useState } from "react";
import Dropzone from "./components/Dropzone";
import QueryForm from "./components/QueryForm";
import Citations from "./components/Citations";
import Toast, { makeToaster } from "./components/Toast";
import { Skeleton } from "./components/Loading";
import History, { pushHistory } from "./components/History";

type SuggestResponse = { suggestions: string[] };

function fileNameForMemo(q: string) {
  const ts = new Date().toISOString().replace(/[:.]/g, "").replace("Z","Z");
  const slug = q.toLowerCase().replace(/[^a-z0-9\s-]/g,"").trim().split(/\s+/).slice(0,6).join("-") || "memo";
  return `memo_${ts}_${slug}.json`;
}

export default function App() {
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [answer, setAnswer] = useState<string>("");
  const [cites, setCites] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [toasts, setToasts] = useState<any[]>([]);
  const [showAbout, setShowAbout] = useState(false);
  const toast = makeToaster(setToasts);

  useEffect(() => {
    fetch("/suggestions", { credentials: "include" })
      .then((r) => r.json())
      .then((d: SuggestResponse) => setSuggestions(d.suggestions || []))
      .catch(() => setSuggestions([]));
  }, []);

  async function onAsk(q: string, filters: any, topK: number, probes: number) {
    setLoading(true); setAnswer(""); setCites([]);
    toast("Searching…", "info");
    try {
      pushHistory(q);
      const res = await fetch("/query", {
        method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include",
        body: JSON.stringify({ q, filters, top_k: topK, probes })
      });
      const data = await res.json();
      setAnswer(data.answer ?? "No evidence found.");
      setCites(data.citations ?? []);
      if (data.citations?.length) {
        const n = data.citations.length;
        toast(`Found ${n} citation${n === 1 ? "" : "s"}.`, "ok");
      } else {
        toast("No evidence found.", "info");
      }
    } catch {
      setAnswer("Request failed."); toast("Request failed.", "err");
    } finally { setLoading(false); }
  }

  async function onExportMemo(q: string, filters: any, topK: number, probes: number) {
    if (!q.trim()) { toast("Enter a question first.", "info"); return; }
    try {
      const res = await fetch("/generate/memo", {
        method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include",
        body: JSON.stringify({ q, filters, top_k: topK, probes })
      });
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data.artifact, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = fileNameForMemo(q);
      a.click();
      URL.revokeObjectURL(a.href);
      toast("Memo exported.", "ok");
    } catch { toast("Export failed.", "err"); }
  }

  return (
    <div className="container">
      <header className="hdr">
        <div className="brand"><span className="brand-dot" />CiteSpine</div>
        <button className="pill" onClick={()=>setShowAbout(true)} aria-label="About this demo">Demo</button>
      </header>

      {showAbout && (
        <div className="sheet" role="dialog" aria-modal="true">
          <div className="sheet-box">
            <h3>About this demo</h3>
            <p>This is an invite‑gated preview. Upload a public PDF, ask a question, and see citations. We never claim without evidence.</p>
            <div className="right"><button className="btn" onClick={()=>setShowAbout(false)}>Close</button></div>
          </div>
        </div>
      )}

      <section className="grid">
        <div className="card">
          <h2>Upload</h2>
          <p className="muted">Drop a PDF here. We'll parse it and make it searchable.</p>
          <Dropzone notify={toast} />
        </div>
        <div className="card">
          <h2>Ask</h2>
          <p className="muted">Type a question or click a suggestion.</p>
          <div className="chips">
            {suggestions.map((s) => (
              <button key={s} className="chip" onClick={() => onAsk(s, {}, 10, 15)}>{s}</button>
            ))}
          </div>
          <QueryForm onAsk={onAsk} onExportMemo={onExportMemo} loading={loading} />
        </div>
      </section>

      <section className="card">
        <h2>Answer</h2>
        {loading ? <Skeleton lines={4} /> : <pre className="answer">{answer || "—"}</pre>}
        <h3>Citations</h3>
        {loading ? <Skeleton lines={3} /> : <Citations items={cites} />}
      </section>

      <History onPick={(q)=>onAsk(q, {}, 10, 15)} />

      <footer className="ftr">No citation → no claim.</footer>

      <Toast items={toasts} onClose={(id)=>setToasts(list=>list.filter(t=>t.id!==id))}/>
    </div>
  );
}
