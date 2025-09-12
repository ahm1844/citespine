import React, { useMemo, useState } from "react";
import type { Overview, OverviewCitation } from "../types";

function sanitize(md: string): string {
  // VERY minimal sanitizer to strip script tags; replace if you add a real lib later
  return md.replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, "");
}

type Props = { overview: Overview | null };

export default function DocumentOverview({ overview }: Props) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [expandedCitation, setExpandedCitation] = useState<string | null>(null);

  if (!overview) {
    return null;
  }

  const getCitationsForIds = (citationIds: string[]) => {
    if (!overview) return [];
    return overview.citations.filter(c => citationIds.includes(c.id));
  };

  const renderCitationChips = (citationIds: string[]) => {
    const sectionCitations = getCitationsForIds(citationIds);
    return sectionCitations.map(citation => (
      <button
        key={citation.id}
        className="citation-chip"
        onClick={() => setExpandedCitation(
          expandedCitation === citation.id ? null : citation.id
        )}
        title={`${citation.section_path} - Page ${citation.page}`}
      >
        p.{citation.page}
      </button>
    ));
  };

  const renderExpandedCitation = (citationId: string) => {
    if (!overview) return null;
    const citation = overview.citations.find(c => c.id === citationId);
    if (!citation) return null;
    const txt = citation.text || "";
    const parts: Array<{ text: string; hl: boolean }> = [];
    let idx = 0;
    const sorted = [...(citation.highlights || [])].sort((a, b) => a.start - b.start);
    for (const h of sorted) {
      if (h.start > idx) parts.push({ text: txt.slice(idx, h.start), hl: false });
      parts.push({ text: txt.slice(h.start, h.end), hl: true });
      idx = h.end;
    }
    if (idx < txt.length) parts.push({ text: txt.slice(idx), hl: false });

    return (
      <div className="cite-expand">
        <div className="cite-meta">
          <strong>{citation.section_path}</strong> - Page {citation.page}
        </div>
        <div className="cite-text">
          {parts.map((p, i) =>
            p.hl ? <mark key={i} className="hl">{p.text}</mark> : <span key={i}>{p.text}</span>
          )}
        </div>
      </div>
    );
  };

  const renderSection = (title: string, content: OverviewSection | OverviewSection[], isArray = false) => {
    if (isArray) {
      const items = content as OverviewSection[];
      if (!items.length) return null;
      
      return (
        <div className="overview-section">
          <h5>{title}</h5>
          {items.map((item, i) => (
            <div key={i} className="overview-item">
              <p>{item.text}</p>
              <div className="citations-row">
                {renderCitationChips(item.citation_ids)}
              </div>
            </div>
          ))}
        </div>
      );
    } else {
      const item = content as OverviewSection;
      if (!item.text) return null;
      
      return (
        <div className="overview-section">
          <h5>{title}</h5>
          <p>{item.text}</p>
          <div className="citations-row">
            {renderCitationChips(item.citation_ids)}
          </div>
        </div>
      );
    }
  };

  return (
    <div className="overview-card">
      <div className="overview-title">
        <span>📄</span>
        <span>Document Overview</span>
        <button 
          className="collapse-btn"
          onClick={() => setIsCollapsed(!isCollapsed)}
          aria-label={isCollapsed ? "Expand overview" : "Collapse overview"}
        >
          {isCollapsed ? "▶" : "▼"}
        </button>
      </div>

      {!isCollapsed && (
        <>
          <div className="overview-summary">
            {/* render markdown as plain text or sanitized HTML */}
            <p dangerouslySetInnerHTML={{ __html: sanitize(overview.overview_markdown) }} />
          </div>

          <div className="overview-grid">
            {renderSection("Purpose", overview.purpose)}
            {renderSection("Scope", overview.scope)}
            {renderSection("Key Requirements", overview.key_requirements, true)}
            {renderSection("Effective Dates", overview.effective_dates, true)}
            {renderSection("Amendments", overview.amendments, true)}
            {renderSection("Affected Parties", overview.affected_parties)}
          </div>

          {expandedCitation && renderExpandedCitation(expandedCitation)}
        </>
      )}
    </div>
  );
}
