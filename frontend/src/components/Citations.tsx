import React from "react";

export default function Citations({ items }:{ items:any[] }) {
  if (!items || !items.length) {
    return <p className="empty">Citations will appear here when evidence supports the answer.</p>;
  }
  return (
    <div className="cites">
      {items.map((c, idx) => (
        <div key={idx} className="cite">
          <div className="meta">
            <span className="badge">{c.framework || "-"}</span>
            <span className="badge">{c.jurisdiction || "-"}</span>
            <span className="badge">{c.doc_type || "-"}</span>
            <span className="badge">{c.authority_level || "-"}</span>
            <span className="muted">p.{c.page_start ?? "?"}–{c.page_end ?? "?"}</span>
          </div>
          <div className="snippet">{c.text}</div>
        </div>
      ))}
    </div>
  );
}
