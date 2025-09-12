import React, { useCallback, useState } from "react";

const MAX_MB = 25;

export default function Dropzone({
  notify,
  onAnalysisStart,
  onClearAnswer,
}: {
  notify?: (msg: string, kind?: "ok" | "err" | "info") => void;
  onAnalysisStart?: (sourceId: string) => void;
  onClearAnswer?: () => void;
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
      console.log("dropzone.upload.start", { filename: file.name });
      const res = await fetch("/upload", { method: "POST", credentials: "include", body: fd });
      const data = await res.json();
      console.log("dropzone.upload.response", { data });
      
      if (data.accepted) { 
        setMsg("Uploaded ✓ - Analyzing document..."); 
        notify?.("Uploaded ✓ - Analyzing...", "info");
        // Clear previous Q&A to avoid confusing carry-over answers
        onClearAnswer?.();
        // Start analysis polling
        if (data.source_id && onAnalysisStart) {
          console.log("dropzone.trigger_analysis", { sourceId: data.source_id, hasCallback: !!onAnalysisStart });
          onAnalysisStart(data.source_id);
        } else {
          console.warn("dropzone.no_analysis_trigger", { sourceId: data.source_id, hasCallback: !!onAnalysisStart });
        }
      }
      else { 
        console.error("dropzone.upload.rejected", data);
        setMsg("Upload failed."); notify?.("Upload failed.", "err"); 
      }
    } catch (e) {
      console.error("dropzone.upload.error", e);
      setMsg("Upload failed."); notify?.("Upload failed.", "err");
    } finally { setBusy(false); }
  }, [notify, onAnalysisStart, onClearAnswer]);

  const onDrop = (e: React.DragEvent) => { e.preventDefault(); e.stopPropagation(); setHover(false);
    const file = e.dataTransfer.files?.[0]; if (file) upload(file);
  };
  const onPick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (file) upload(file);
  };

  return (
    <div className={`drop card ${hover ? "hover" : ""} ${busy ? "busy":""}`}
         onDragOver={(e)=>{e.preventDefault(); setHover(true);}}
         onDragLeave={()=>setHover(false)}
         onDrop={onDrop}
         aria-busy={busy}>
      <div className="pulse" aria-hidden />
      <p>{msg}</p>
      <label className="btn" style={{display:"inline-block",cursor:"pointer"}}>
        <input type="file" accept="application/pdf" onChange={onPick} style={{display:"none"}} />
        Choose PDF
      </label>
    </div>
  );
}

