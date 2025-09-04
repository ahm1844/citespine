import React, { useEffect, useState } from "react";

type Item = { q: string; ts: number };

export default function History({ onPick }:{ onPick:(q:string)=>void }) {
  const [items, setItems] = useState<Item[]>([]);
  useEffect(() => {
    try { const raw = localStorage.getItem("cs_history"); if (raw) setItems(JSON.parse(raw)); } catch {}
  }, []);
  if (!items.length) return null;
  return (
    <div className="card">
      <h3>Recent questions</h3>
      <div className="hist">
        {items.slice(0,8).map(it => (
          <button key={it.ts} className="chip" onClick={()=>onPick(it.q)} title={new Date(it.ts).toLocaleString()}>
            {it.q.length > 60 ? it.q.slice(0,60)+"…" : it.q}
          </button>
        ))}
      </div>
    </div>
  );
}

export function pushHistory(q: string) {
  try {
    const raw = localStorage.getItem("cs_history");
    const arr: Item[] = raw ? JSON.parse(raw) : [];
    const next = [{ q, ts: Date.now() }, ...arr.filter(x => x.q !== q)].slice(0,20);
    localStorage.setItem("cs_history", JSON.stringify(next));
  } catch {}
}
