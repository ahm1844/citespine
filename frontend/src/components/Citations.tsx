import React from "react";

export default function Citations({ items }: { items: any[] }) {
  if (!items || !items.length) {
    return <p className="empty">Citations will appear here when evidence supports the answer.</p>;
  }
  return (
    <div className="cites">
      {items.map((e:any, i:number) => (
        <div key={e.chunk_id || i} className="cite">
          <div className="meta">
            {e.framework && <span className="badge">{e.framework}</span>}
            {e.jurisdiction && <span className="badge">{e.jurisdiction}</span>}
            {e.doc_type && <span className="badge">{e.doc_type}</span>}
            {e.authority_level && <span className="badge">{e.authority_level}</span>}
            {e.page_start && <span className="badge">p. {e.page_start}{e.page_end && e.page_end!==e.page_start ? `–${e.page_end}` : ""}</span>}
            {e.section_path && <span className="badge">{e.section_path}</span>}
          </div>
          <div className="snippet">
            {Array.isArray(e.highlights) && e.highlights.length > 0
              ? (() => {
                  const txt = e.text || "";
                  const spans = [...e.highlights].sort((a:any,b:any)=>a.start-b.start);
                  const parts: Array<{t:string;hl:boolean}> = [];
                  let idx = 0;
                  for (const h of spans) {
                    if (h.start > idx) parts.push({ t: txt.slice(idx, h.start), hl:false });
                    parts.push({ t: txt.slice(h.start, h.end), hl:true });
                    idx = h.end;
                  }
                  if (idx < txt.length) parts.push({ t: txt.slice(idx), hl:false });
                  return parts.map((p, k) => p.hl
                    ? <mark key={k} className="hl">{p.t}</mark>
                    : <span key={k}>{p.t}</span>);
                })()
              : (e.text || "")}
          </div>
        </div>
      ))}
    </div>
  );
}
