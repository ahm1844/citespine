import React from "react";

export default function Footer() {
  return (
    <footer className="ftr-outer">
      <div className="ftr-inner">
        <div className="ftr-left">No citation → no claim.</div>
        <div className="ftr-links">
          <a href="/site">Terms</a><span>•</span>
          <a href="/site">Privacy</a><span>•</span>
          <a href="/site">Contact</a>
        </div>
        <div className="ftr-right">v0.1.0 • Demo</div>
      </div>
    </footer>
  );
}
