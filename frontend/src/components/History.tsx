import React, { useEffect, useMemo, useState } from "react";

type Item = { q: string; ts: number; pinned?: boolean };
const KEY = "cs_history";

function load(): Item[] {
  try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; }
}
function save(items: Item[]) {
  try { localStorage.setItem(KEY, JSON.stringify(items.slice(0,50))); } catch {}
}

export function pushHistory(q: string) {
  try {
    const arr = load();
    const next = [{ q, ts: Date.now(), pinned:false }, ...arr.filter(x => x.q !== q)];
    save(next);
  } catch {}
}

export default function History({
  onPick, suggestions = [],
}: { onPick: (q: string) => void; suggestions?: string[] }) {
  const [items, setItems] = useState<Item[]>([]);
  const [search, setSearch] = useState("");

  useEffect(() => { setItems(load()); }, []);

  const filtered = useMemo(() => {
    const s = search.trim().toLowerCase();
    const arr = s ? items.filter(i => i.q.toLowerCase().includes(s)) : items;
    return [...arr].sort((a,b) => (b.pinned?1:0)-(a.pinned?1:0) || b.ts - a.ts).slice(0,12);
  }, [items, search]);

  const togglePin = (ts:number) => { const n = items.map(i => i.ts===ts ? {...i, pinned:!i.pinned} : i); setItems(n); save(n); };
  const remove    = (ts:number) => { const n = items.filter(i => i.ts!==ts); setItems(n); save(n); };

  return (
    <div className="card">
      <div className="row" style={{marginTop:0, alignItems:"center"}}>
        <h3 style={{margin:0}}>Recent questions</h3>
        {items.length > 0 && (
          <input placeholder="Search history…" value={search} onChange={(e)=>setSearch(e.target.value)} />
        )}
      </div>

      {items.length === 0 ? (
        <div className="empty-card">
          <p>No recent questions yet. Try a suggestion to get started:</p>
          <div className="chips">
            {(suggestions.slice(0,6)).map((s, i) =>
              <button key={i} className="chip" onClick={()=>onPick(s)}>{s}</button>
            )}
          </div>
        </div>
      ) : (
        <div className="hist-list">
          {filtered.map(it => (
            <div key={it.ts} className="hist-item">
              <button className="hist-text" title={new Date(it.ts).toLocaleString()} onClick={()=>onPick(it.q)}>
                {it.q.length>80? it.q.slice(0,80)+"…" : it.q}
              </button>
              <div className="hist-actions">
                <button className={`icon ${it.pinned?"on":""}`} title={it.pinned?"Unpin":"Pin"} onClick={()=>togglePin(it.ts)}>★</button>
                <button className="icon" title="Remove" onClick={()=>remove(it.ts)}>✕</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}