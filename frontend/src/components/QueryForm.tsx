import React, { useEffect, useState } from "react";

export default function QueryForm({
  preset, suggestions = [], onAsk, onExportMemo,
}: {
  preset?: string;
  suggestions?: string[];
  onAsk: (q: string, filters: any, topK: number, probes: number) => void;
  onExportMemo: (q: string, filters: any, topK: number, probes: number) => void;
}) {
  const [q, setQ] = useState("");
  const [framework, setFramework] = useState("");
  const [jurisdiction, setJurisdiction] = useState("");
  const [docType, setDocType] = useState("");
  const [authority, setAuthority] = useState("");
  const [asOf, setAsOf] = useState("");
  const [topK, setTopK] = useState(10);
  const [probes, setProbes] = useState(15);

  useEffect(() => { if (preset) setQ(preset); }, [preset]);

  const submit = () => onAsk(q, { framework, jurisdiction, doc_type: docType, authority_level: authority, as_of: asOf }, topK, probes);
  const exportMemo = () => onExportMemo(q, { framework, jurisdiction, doc_type: docType, authority_level: authority, as_of: asOf }, topK, probes);

  const onKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") { e.preventDefault(); submit(); }
  };

  return (
    <div className="card">
      <h2>Ask</h2>
      <p className="muted">Type a question or click a suggestion.</p>

      {suggestions.length > 0 && (
        <div className="chips" aria-label="Suggestions">
          {suggestions.slice(0,6).map((s, i) =>
            <button key={i} className="chip" onClick={()=>setQ(s)}>{s}</button>
          )}
        </div>
      )}

      <textarea
        className="ta"
        placeholder="e.g., What does PCAOB require for ICFR audits?"
        value={q}
        onChange={(e)=>setQ(e.target.value)}
        onKeyDown={onKey}
        rows={5}
        maxLength={1200}
        style={{maxHeight:220}}
      />
      <div className="help">⌘/Ctrl + Enter to ask</div>

      <div className="row">
        <input placeholder="Framework (e.g., PCAOB, ESMA)" value={framework}     onChange={(e)=>setFramework(e.target.value)} />
        <input placeholder="Jurisdiction (e.g., US, EU)"   value={jurisdiction}  onChange={(e)=>setJurisdiction(e.target.value)} />
      </div>
      <div className="row">
        <input placeholder="Doc Type (e.g., standard, filing)" value={docType}   onChange={(e)=>setDocType(e.target.value)} />
        <input placeholder="Authority (e.g., authoritative)"   value={authority} onChange={(e)=>setAuthority(e.target.value)} />
      </div>
      <div className="row">
        <input placeholder="As‑of (YYYY‑MM‑DD)" value={asOf} onChange={(e)=>setAsOf(e.target.value)} />
        <div className="row small">
          <input className="num" type="number" min={1} value={topK}  onChange={(e)=>setTopK(parseInt(e.target.value || "10"))} />
          <input className="num" type="number" min={1} value={probes} onChange={(e)=>setProbes(parseInt(e.target.value || "15"))} />
        </div>
      </div>

      <div style={{display:"flex",gap:"12px",marginTop:"8px"}}>
        <button className="btn" onClick={submit}>Ask</button>
        <button className="btn ghost" onClick={exportMemo}>Export memo</button>
      </div>
    </div>
  );
}