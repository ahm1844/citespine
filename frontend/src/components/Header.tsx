import React from "react";

type Props = {
  onOpenAbout: () => void;
  onOpenDocs: () => void;
  onOpenApi: () => void;
  onOpenSecurity: () => void;
  showLogo?: boolean;
};

export default function Header({
  onOpenAbout, onOpenDocs, onOpenApi, onOpenSecurity, showLogo = true,
}: Props) {
  // ✅ Safe string concatenation; works with Vite base and /app mount
  const base = (import.meta.env?.BASE_URL ?? "/");
  const logoUrl = `${base}${base.endsWith("/") ? "" : "/"}citespine-logo.png`;

  return (
    <header className="hdr">
      <div className="brand">
        {showLogo && (
                  <img
          src={logoUrl}
          alt="CiteSpine logo"
          className="logo-img logo-tight"   // ← add logo-tight while you use a padded PNG
          onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
        />
        )}
      </div>

      <nav className="nav" aria-label="Primary">
        <button className="btn-link" onClick={onOpenDocs}>Docs</button>
        <button className="btn-link" onClick={onOpenApi}>API</button>
        <button className="btn-link" onClick={onOpenSecurity}>Security</button>
      </nav>

      <button className="pill" onClick={onOpenAbout} aria-label="About this demo">
        Demo
      </button>
    </header>
  );
}
