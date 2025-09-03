import React, { useState } from "react";

export default function QueryForm({ onAsk, loading }:{ onAsk:(q:string,f:any,k:number,p:number)=>void, loading:boolean }) {
  const [q, setQ] = useState("");
  const [topK, setTopK] = useState(10);
  const [probes, setProbes] = useState(15);
  const [filters, setFilters] = useState<any>({});

  const submit = (e: React.FormEvent) => { e.preventDefault(); onAsk(q, filters, topK, probes); };

  return (
    <form onSubmit={submit} className="form">
      <textarea className="ta" placeholder="e.g., What does PCAOB require for ICFR audits?" value={q} onChange={(e)=>setQ(e.target.value)} />
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
          <input type="number" min={1} value={topK} onChange={(e)=>setTopK(parseInt(e.target.value||"10"))}/>
          <input type="number" min={1} value={probes} onChange={(e)=>setProbes(parseInt(e.target.value||"15"))}/>
        </div>
      </div>
      <button className="btn" type="submit" disabled={loading}>{loading ? "Searching…" : "Ask"}</button>
    </form>
  );
}
