import React, { useCallback, useState } from "react";

const MAX_MB = 25;

export default function Dropzone({
  notify,
}: {
  notify?: (msg: string, kind?: "ok" | "err" | "info") => void;
}) {
  const [msg, setMsg] = useState("Place or upload your PDF here");
  const [busy, setBusy] = useState(false);
  const [hover, setHover] = useState(false);

  const upload = useCallback(async (file: File) => {
    if (!file?.name.toLowerCase().endsWith(".pdf")) {
      setMsg("Please select a PDF."); notify?.("Upload failed.", "err"); return;
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      setMsg(`File too large (> ${MAX_MB}MB).`); notify?.("Upload failed.", "err"); return;
    }
    setBusy(true); setMsg("Uploading…"); notify?.("Uploading…", "info");
    const fd = new FormData(); fd.append("file", file);
    try {
      const res = await fetch("/upload", { method: "POST", credentials: "include", body: fd });
      const data = await res.json();
      if (data.accepted) { setMsg("Uploaded and indexed ✓"); notify?.("Indexed ✓", "ok"); }
      else { setMsg("Upload failed."); notify?.("Upload failed.", "err"); }
    } catch {
      setMsg("Upload failed."); notify?.("Upload failed.", "err");
    } finally { setBusy(false); }
  }, [notify]);

  const onInput = (e: React.ChangeEvent<HTMLInputElement>) => { const f = e.target.files?.[0]; if (f) upload(f); };
  const onDragOver = (e: React.DragEvent) => { e.preventDefault(); setHover(true); };
  const onDragLeave = () => setHover(false);
  const onDropEvt = (e: React.DragEvent) => { e.preventDefault(); setHover(false); const f = e.dataTransfer.files?.[0]; if (f) upload(f); };

  return (
    <div className={`drop ${busy ? "busy" : ""} ${hover ? "hover" : ""}`} onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDropEvt}>
      <div className="pulse" />
      <p>{msg}</p>
      <input id="file" type="file" accept="application/pdf" onChange={onInput} hidden />
      <label className="btn" htmlFor="file">Choose PDF</label>
    </div>
  );
}
