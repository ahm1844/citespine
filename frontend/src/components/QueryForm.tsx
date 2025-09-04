import React, { useEffect, useRef, useState } from "react";

export default function QueryForm({
  onAsk, loading, onExportMemo
}:{ onAsk:(q:string,f:any,k:number,p:number)=>void; loading:boolean; onExportMemo:(q:string,f:any,k:number,p:number)=>void; }) {
  const [q, setQ] = useState("");
  const [topK, setTopK] = useState(10);
  const [probes, setProbes] = useState(15);
  const [filters, setFilters] = useState<any>({});
  const [err, setErr] = useState<string>("");

  const ta = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "enter") {
        e.preventDefault(); submit();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [q, filters, topK, probes]);

  function submit() {
    if (!q.trim()) { setErr("Question cannot be empty."); ta.current?.focus(); return; }
    setErr(""); onAsk(q, filters, topK, probes);
  }

  return (
    <div>
      <form onSubmit={(e)=>{e.preventDefault(); submit();}} className="form">
        <textarea
          ref={ta}
          className={`ta ${err ? "err" : ""}`}
          placeholder="e.g., What does PCAOB require for ICFR audits?"
          value={q} onChange={(e)=>setQ(e.target.value)}
        />
        {err ? <div className="help errc">{err}</div> : <div className="help">⌘/Ctrl + Enter to ask</div>}
        <div className="row">
          <input placeholder="Framework (e.g., PCAOB, ESMA)" onChange={(e)=>setFilters({...filters, framework:e.target.value||undefined})}/>
          <input placeholder="Jurisdiction (e.g., US, EU)" onChange={(e)=>setFilters({...filters, jurisdiction:e.target.value||undefined})}/>
        </div>
        <div className="row">
          <input placeholder="Doc Type (e.g., standard, filing)" onChange={(e)=>setFilters({...filters, doc_type:e.target.value||undefined})}/>
          <input placeholder="Authority (e.g., authoritative)" onChange={(e)=>setFilters({...filters, authority_level:e.target.value||undefined})}/>
        </div>
        <div className="row">
          <input placeholder="As-of (YYYY-MM-DD)" onChange={(e)=>setFilters({...filters, as_of:e.target.value||undefined})}/>
          <div className="row small">
            <input className="num" type="number" min={1} value={topK} onChange={(e)=>setTopK(parseInt(e.target.value||"10"))}/>
            <input className="num" type="number" min={1} value={probes} onChange={(e)=>setProbes(parseInt(e.target.value||"15"))}/>
          </div>
        </div>
        <div className="row">
          <button className="btn" type="submit" disabled={loading}>{loading ? "Searching…" : "Ask"}</button>
          <button className="btn ghost" type="button" onClick={()=>onExportMemo(q, filters, topK, probes)} disabled={loading || !q.trim()}>Export memo</button>
        </div>
      </form>
    </div>
  );
}
