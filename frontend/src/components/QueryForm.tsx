import React, { useEffect, useState } from "react";

type Suggestion = {
  question: string;
  expected_evidence_type?: string;
  boost_terms?: string[];
  category?: string;
  confidence?: number;
  focus_source_id?: string;
};

export default function QueryForm({
  preset, suggestions = [], onAsk, onExportMemo,
}: {
  preset?: string;
  suggestions?: Suggestion[];
  onAsk: (q: string, filters: any, topK: number, probes: number, suggestion?: Suggestion) => void;
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

  const [showSuggestions, setShowSuggestions] = useState(false);

  useEffect(() => { if (preset) setQ(preset); }, [preset]);

  // Animate suggestions appearance
  useEffect(() => {
    if (suggestions.length > 0) {
      setTimeout(() => setShowSuggestions(true), 100);
    } else {
      setShowSuggestions(false);
    }
  }, [suggestions]);

  const submit = () => onAsk(q, { framework, jurisdiction, doc_type: docType, authority_level: authority, as_of: asOf }, topK, probes);
  const exportMemo = () => onExportMemo(q, { framework, jurisdiction, doc_type: docType, authority_level: authority, as_of: asOf }, topK, probes);

  // Handle suggestion click - execute immediately
  const onSuggestionClick = (suggestion: Suggestion) => {
    const filters = { framework, jurisdiction, doc_type: docType, authority_level: authority, as_of: asOf };
    onAsk(suggestion.question, filters, topK, probes, suggestion);
  };

  const onKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") { e.preventDefault(); submit(); }
  };

  return (
    <div className="card">
      <h2>Ask</h2>
      <p className="muted">Type a question or click a suggestion.</p>

      {suggestions.length > 0 && (
        <div className={`suggestions-container ${showSuggestions ? 'show' : ''}`}>
          <h4 style={{fontSize: "14px", fontWeight: 600, margin: "0 0 8px 0", color: "#a9b0c0"}}>
            Smart Questions (Click to Answer)
          </h4>
          <div className="chips animated-suggestions" aria-label="Document Suggestions">
            {suggestions.slice(0,5).map((suggestion, i) => (
              <button 
                key={i} 
                className="chip suggestion-chip" 
                onClick={() => onSuggestionClick(suggestion)}
                style={{
                  animationDelay: `${i * 0.1}s`,
                  position: 'relative'
                }}
                aria-label={`Ask: ${suggestion.question}`}
                title={`${suggestion.category || 'Question'} • Confidence: ${Math.round((suggestion.confidence || 0.5) * 100)}%`}
              >
                <span className="suggestion-text">{suggestion.question}</span>
                {suggestion.confidence && (
                  <span className="confidence-badge" style={{
                    fontSize: '10px',
                    backgroundColor: '#2a3248',
                    color: '#a9b0c0',
                    padding: '2px 4px',
                    borderRadius: '4px',
                    marginLeft: '6px'
                  }}>
                    {Math.round(suggestion.confidence * 100)}%
                  </span>
                )}
              </button>
            ))}
          </div>
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