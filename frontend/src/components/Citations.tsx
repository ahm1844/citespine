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
            {typeof e.page_start !== "undefined" && typeof e.page_end !== "undefined" && (
              <span className="badge">pp. {e.page_start}-{e.page_end}</span>
            )}
            {e.section_path && <span className="badge">{e.section_path}</span>}
          </div>
          <div className="snippet">{e.text}</div>
        </div>
      ))}
    </div>
  );
}
