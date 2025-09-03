import React, { useEffect, useState } from "react";
import Dropzone from "./components/Dropzone";
import QueryForm from "./components/QueryForm";
import Citations from "./components/Citations";

export default function App() {
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [answer, setAnswer] = useState("-");
  const [cites, setCites] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch("/suggestions", { credentials: "include" })
      .then((r) => r.json())
      .then((d) => setSuggestions(d.suggestions || []))
      .catch(() => setSuggestions([]));
  }, []);

  async function onAsk(q: string, filters: any, topK: number, probes: number) {
    setLoading(true); setAnswer("-"); setCites([]);
    try {
      const res = await fetch("/query", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ q, filters, top_k: topK, probes })
      });
      const data = await res.json();
      setAnswer(data.answer ?? "No evidence found.");
      setCites(data.citations ?? []);
    } catch {
      setAnswer("Request failed.");
    } finally { setLoading(false); }
  }

  return (
    <div className="container">
      <header className="hdr">
        <div className="brand">CiteSpine</div>
        <div className="tag">Demo</div>
      </header>

      <section className="grid">
        <div className="card">
          <h2>Upload</h2>
          <p className="muted">Drop a PDF here. We'll parse it and make it searchable.</p>
          <Dropzone />
        </div>
        <div className="card">
          <h2>Ask</h2>
          <p className="muted">Type a question or click a suggestion.</p>
          <div className="chips">
            {suggestions.map((s) => (
              <button key={s} className="chip" onClick={() => onAsk(s, {}, 10, 15)}>{s}</button>
            ))}
          </div>
          <QueryForm onAsk={onAsk} loading={loading} />
        </div>
      </section>

      <section className="card">
        <h2>Answer</h2>
        <pre className="answer">{answer}</pre>
        <h3>Citations</h3>
        <Citations items={cites} />
      </section>

      <footer className="ftr">No citation → no claim.</footer>
    </div>
  );
}
