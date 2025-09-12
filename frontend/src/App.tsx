import React, { useEffect, useRef, useState } from "react";
import Header from "./components/Header";
import Footer from "./components/Footer";
import Dropzone from "./components/Dropzone";
import QueryForm from "./components/QueryForm";
import Citations from "./components/Citations";
import DocumentOverview from "./components/DocumentOverview";
import History, { pushHistory } from "./components/History";
import Toast, { makeToaster } from "./components/Toast";
import type { Overview, OverviewCitation } from "./types";

type Cite = {
  chunk_id?: string; text?: string; framework?: string; jurisdiction?: string;
  doc_type?: string; authority_level?: string; page_start?: number; page_end?: number; section_path?: string;
};

type Suggestion = {
  question: string;
  expected_evidence_type?: string;
  boost_terms?: string[];
  category?: string;
  confidence?: number;
  focus_source_id?: string;
};

// Types imported from ./types.ts

export default function App() {
  const [about, setAbout] = useState(false);
  const [docsOpen, setDocsOpen] = useState(false);
  const [apiOpen, setApiOpen] = useState(false);
  const [secOpen, setSecOpen] = useState(false);

  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [presetQ, setPresetQ] = useState<string>("");
  
  // Document analysis states
  const [analyzingSource, setAnalyzingSource] = useState<string>("");
  const [analysisProgress, setAnalysisProgress] = useState<string>("");
  
  // Document overview states
  const [overview, setOverview] = useState<Overview | null>(null);
  const overviewRef = useRef<HTMLDivElement|null>(null);
  const pollCtl = useRef<AbortController|null>(null);
  const queryCtl = useRef<AbortController|null>(null);

  const [answer, setAnswer] = useState<string>("-");
  const [cites, setCites] = useState<Cite[]>([]);
  const [metrics, setMetrics] = useState<any>({});
  const [loading, setLoading] = useState(false);

  const [toasts, setToasts] = useState<any[]>([]);
  const toast = makeToaster(setToasts);

  useEffect(() => {
    // No static suggestions - they come from document analysis now
    setSuggestions([]);
  }, []);

  // Handle document analysis after upload
  async function pollAnalysis(sourceId: string) {
    console.log("pollAnalysis.start", { sourceId });
    setAnalyzingSource(sourceId);
    setAnalysisProgress("analyzing");
    
    // cancel any previous poll
    if (pollCtl.current) pollCtl.current.abort();
    pollCtl.current = new AbortController();
    const signal = pollCtl.current.signal;

    // Poll until ready
    for (let i = 0; i < 60; i++) { // 60 second timeout
      try {
        if (signal.aborted) return;
        const res = await fetch(`/analysis/${sourceId}`, { credentials: "include", signal });
        const data = await res.json();
        console.log("pollAnalysis.response", { sourceId, data });
        
        if (data.ready) {
          console.log("pollAnalysis.ready", { sourceId, questionsCount: data.questions?.length, hasOverview: !!data.overview });
          
          // Set overview and overview citations
          setOverview(data.overview || null);
          
          // Set suggestions 
          setSuggestions(data.questions || []);
          
          // Clear analysis progress
          setAnalyzingSource("");
          setAnalysisProgress("");
          
          toast(`Generated ${data.questions?.length || 0} questions from document`, "ok");

          // Bring the overview into view and focus it for discoverability
          setTimeout(() => {
            overviewRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
            overviewRef.current?.focus?.();
          }, 10);
          return;
        }
        
        await new Promise(resolve => setTimeout(resolve, 1000));
      } catch (e) {
        console.warn("Analysis polling error:", e);
      }
    }
    
    // Timeout
    console.log("pollAnalysis.timeout", { sourceId });
    setAnalyzingSource("");
    setAnalysisProgress("");
    toast("Analysis timed out - please try again", "err");
  }

  async function onAsk(
    q: string, 
    filters: any, 
    topK: number, 
    probes: number, 
    suggestion?: { question?: string; boost_terms?: string[]; expected_evidence_type?: string; focus_source_id?: string }
  ) {
    setLoading(true); setAnswer(""); setCites([]);
    if (queryCtl.current) queryCtl.current.abort();
    queryCtl.current = new AbortController();
    const signal = queryCtl.current.signal;
    
    toast("Searching…", "info");
    try {
      // Build enhanced query with suggestion data
      const payload: any = { 
        q, 
        filters, 
        top_k: topK, 
        probes 
      };
      
      if (suggestion) {
        payload.focus_source_id = suggestion.focus_source_id;
        payload.expected_evidence_type = suggestion.expected_evidence_type;
        payload.boost_terms = suggestion.boost_terms;
      }
      
      const res = await fetch("/query", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal
      });
      
      if (!res.ok) {
        if (res.status === 429) throw new Error("Rate limit reached. Try again in a minute.");
        if (res.status === 401 || res.status === 403) throw new Error("You're not authorized for this action.");
        if (res.status === 413) throw new Error("File too large for this demo.");
        if (res.status === 415) throw new Error("Unsupported file type (PDF only).");
        const msg = await res.text();
        throw new Error(msg || `HTTP ${res.status}`);
      }
      
      const data = await res.json();
      setAnswer(data.answer ?? "No evidence found.");
      setCites(data.citations ?? []);
      setMetrics(data.metrics ?? {});
      pushHistory(q);
      if (data.citations?.length) toast(`Found ${data.citations.length} citation${data.citations.length===1?"":"s"}.`, "ok");
      else toast("No evidence found.", "info");
    } catch (e:any) {
      if (e.name === 'AbortError') return; // Ignore aborted requests
      setAnswer("Request failed."); toast(`Ask failed: ${e.message || e}`, "err");
    } finally { setLoading(false); }
  }

  async function onExportMemo(q: string, filters: any, topK: number, probes: number) {
    if (!q.trim()) { toast("Enter a question first.", "info"); return; }
    try {
      const res = await fetch("/generate/memo", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ q, filters, top_k: topK, probes })
      });
      const blob = new Blob([JSON.stringify(await res.json(), null, 2)], { type: "application/json" });
      const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "memo.json"; a.click();
      toast("Memo exported.", "ok");
    } catch { toast("Export failed.", "err"); }
  }

  return (
    <div className="container">
      <Header
        onOpenAbout={() => setAbout(true)}
        onOpenDocs={() => setDocsOpen(true)}
        onOpenApi={() => setApiOpen(true)}
        onOpenSecurity={() => setSecOpen(true)}
      />

      {/* Sheets (modals) */}
      {about && (
        <div className="sheet" role="dialog" aria-modal="true" onClick={()=>setAbout(false)}>
          <div className="sheet-box" onClick={(e)=>e.stopPropagation()}>
            <h3>About this demo</h3>
            <p>This is an invite‑gated preview. Upload a PDF, ask a question, and see citations. We never claim without evidence.</p>
            <div style={{display:"flex",justifyContent:"flex-end"}}><button className="btn" onClick={()=>setAbout(false)}>Close</button></div>
          </div>
        </div>
      )}

      {docsOpen && (
        <div className="sheet" role="dialog" aria-modal="true" onClick={()=>setDocsOpen(false)}>
          <div className="sheet-box" onClick={(e)=>e.stopPropagation()}>
            <h3>Docs</h3>
            <p>See README for setup, API reference, and evaluation. This modal keeps the demo flow in one place.</p>
            <a className="nav-link" href="/site">Open docs page</a>
          </div>
        </div>
      )}

      {apiOpen && (
        <div className="sheet" role="dialog" aria-modal="true" onClick={()=>setApiOpen(false)}>
          <div className="sheet-box" onClick={(e)=>e.stopPropagation()}>
            <h3>API</h3>
            <p>Programmatic access uses <code>X-Api-Key</code> and JSON payloads.</p>
            <pre className="answer" style={{whiteSpace:"pre-wrap"}}>
{`curl -X POST http://localhost:8000/v1/query \\
  -H "X-Api-Key: <your-key>" -H "Content-Type: application/json" \\
  -d '{"q":"What does PCAOB require for ICFR?","filters":{},"top_k":10}'`}
            </pre>
            <div style={{display:"flex",justifyContent:"flex-end"}}><button className="btn" onClick={()=>setApiOpen(false)}>Close</button></div>
          </div>
        </div>
      )}

      {secOpen && (
        <div className="sheet" role="dialog" aria-modal="true" onClick={()=>setSecOpen(false)}>
          <div className="sheet-box" onClick={(e)=>e.stopPropagation()}>
            <h3>Security</h3>
            <p>Local‑first, invite‑gated. Evidence‑only responses. No training on your data. Remove content any time.</p>
            <div style={{display:"flex",justifyContent:"flex-end"}}><button className="btn" onClick={()=>setSecOpen(false)}>Close</button></div>
          </div>
        </div>
      )}

      {/* Document Overview - appears after analysis */}
      {overview && (
        <section aria-label="Document Overview">
          <div ref={overviewRef} tabIndex={-1}>
            <DocumentOverview overview={overview} />
          </div>
        </section>
      )}

      {/* Upload + Ask */}
      <div className="grid">
        <div className="card">
          <h2>Upload</h2>
          <p className="muted">Drop a PDF here. We'll parse it and make it searchable.</p>
          <Dropzone 
            notify={toast} 
            onAnalysisStart={pollAnalysis}
            onClearAnswer={() => { setAnswer(""); setCites([]); }}
          />
          {analyzingSource && (
            <div className="analysis-status" style={{marginTop: "12px", padding: "8px", backgroundColor: "#171c2a", borderRadius: "8px"}}>
              <div className="skel">
                <div className="skel-line" style={{height: "8px", marginBottom: "4px"}}></div>
              </div>
              <p style={{fontSize: "14px", color: "#a9b0c0", margin: "4px 0 0 0"}}>Analyzing document and generating questions...</p>
            </div>
          )}
        </div>

        <QueryForm
          preset={presetQ}
          suggestions={suggestions}
          onAsk={onAsk}
          onExportMemo={onExportMemo}
        />
      </div>

      {/* Question & Answer */}
      <section aria-label="Question & Answer">
        <div className="card section">
          <h3>Answer</h3>
          {loading
            ? <div className="skel"><div className="skel-line"></div><div className="skel-line"></div><div className="skel-line"></div></div>
            : <div className="answer">{answer || "-"}</div>}
        </div>

        {/* Citations */}
        <div className="card section-sm">
          <h3>Citations</h3>
          {loading ? <div className="skel"><div className="skel-line"></div><div className="skel-line"></div></div>
                   : <Citations items={cites} />}
        </div>
      </section>

      {/* Recent questions */}
      <div className="card section-sm">
        <History onPick={(q)=> setPresetQ(q)} suggestions={suggestions.map(s => typeof s === 'string' ? s : s.question)} />
      </div>

      <Footer />

      <Toast items={toasts} onClose={(id)=> setToasts(list => list.filter((t:any) => t.id !== id))} />
    </div>
  );
}