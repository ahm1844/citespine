import React, { useCallback, useState } from "react";

export default function Dropzone() {
  const [msg, setMsg] = useState("Place or upload your PDF here");
  const [busy, setBusy] = useState(false);

  const onDrop = useCallback(async (file: File) => {
    if (!file?.name.toLowerCase().endsWith(".pdf")) {
      setMsg("Please drop a PDF file."); return;
    }
    setBusy(true); setMsg("Uploading…");
    const fd = new FormData(); fd.append("file", file);
    try {
      const res = await fetch("/upload", { method: "POST", credentials: "include", body: fd });
      const data = await res.json();
      if (data.accepted) setMsg("Uploaded and indexed ✓");
      else setMsg("Upload failed: " + (data.errors ? JSON.stringify(data.errors) : "unknown error"));
    } catch { setMsg("Upload failed."); }
    finally { setBusy(false); }
  }, []);

  const onInput = (e: React.ChangeEvent<HTMLInputElement>) => { const f = e.target.files?.[0]; if (f) onDrop(f); };
  const onDragOver = (e: React.DragEvent) => { e.preventDefault(); };
  const onDropEvt = (e: React.DragEvent) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) onDrop(f); };

  return (
    <div className={`drop ${busy ? "busy" : ""}`} onDragOver={onDragOver} onDrop={onDropEvt}>
      <div className="pulse" />
      <p>{msg}</p>
      <input id="file" type="file" accept="application/pdf" onChange={onInput} hidden />
      <label className="btn" htmlFor="file">Choose PDF</label>
    </div>
  );
}
