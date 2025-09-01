"""End-to-end ingest: parse/OCR → normalize → chunk → JSONL; write exceptions.csv."""
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from ..common.constants import RAW_DIR, PROCESSED_DIR, EXCEPTIONS_CSV
from ..common.logging import get_logger
from ..common.progress import log_progress
from .metadata import load_vocab, normalize_record, write_exception_row, compute_source_id
from .parse_pdf import extract_text_by_page
from .ocr import ocr_page
from .chunker import chunk_text, count_tokens

log = get_logger("ingest/runner")

def _load_manifest(raw_dir: Path) -> Dict[str, Dict[str, str]]:
    """Load data/raw/manifest.csv mapping filename -> required metadata fields."""
    mpath = raw_dir / "manifest.csv"
    if not mpath.exists():
        log.warning("manifest.csv missing in data/raw; all docs will be rejected.")
        return {}
    out: Dict[str, Dict[str, str]] = {}
    with mpath.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[row["filename"]] = row
    return out

def run_ingest():
    task = "INGEST"
    log_progress(task, "START", "Reading PDFs and producing processed JSONL")
    raw_dir = Path(RAW_DIR)
    proc_dir = Path(PROCESSED_DIR); proc_dir.mkdir(parents=True, exist_ok=True)
    vocab = load_vocab(Path("config/metadata.yml"))
    manifest_map = _load_manifest(raw_dir)

    accepted = 0
    rejected = 0

    for pdf in raw_dir.glob("*.pdf"):
        filename = pdf.name
        log.info(f"Processing: {filename}")
        meta_row = manifest_map.get(filename, {})
        norm, errs = normalize_record(meta_row, vocab)
        if errs:
            for f, info in errs.items():
                write_exception_row(filename, f, info.get("provided",""), info.get("suggestion",""), "validation_failed")
            log.error(f"Rejected {filename}: metadata validation failed")
            rejected += 1
            continue

        bytes_ = pdf.read_bytes()
        source_id = compute_source_id(bytes_)
        pages = extract_text_by_page(pdf)

        merged = []
        for n, txt in pages:
            tt = (txt or "").strip()
            if len(tt) < 20:
                oc = ocr_page(pdf, n) or ""
                tt = oc if len(oc) > len(tt) else tt
            merged.append(tt)
        full_text = "\n\n".join(merged).strip()
        if not full_text:
            write_exception_row(filename, "text", "", "", "empty_document")
            log.error(f"Rejected {filename}: no text after OCR")
            rejected += 1
            continue

        chunks = chunk_text(full_text)
        if not chunks:
            write_exception_row(filename, "chunking", "", "", "no_chunks_produced")
            log.error(f"Rejected {filename}: chunker produced 0 chunks")
            rejected += 1
            continue

        out_path = proc_dir / f"{source_id}.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for i, c in enumerate(chunks, start=1):
                row = {
                    "source_id": source_id,
                    "title": norm["title"],
                    "doc_type": norm["doc_type"],
                    "framework": norm["framework"],
                    "jurisdiction": norm["jurisdiction"],
                    "authority_level": norm["authority_level"],
                    "effective_date": norm["effective_date"],
                    "version": norm["version"],
                    "section_path": norm["title"],  # naive; can improve later with heading detection
                    "chunk_id": f"{source_id}:{i:04d}",
                    "text": c,
                    "tokens": count_tokens(c),
                    "page_start": 1,
                    "page_end": len(pages),
                    "source_path": str(pdf),
                    "ingest_ts": datetime.utcnow().isoformat()
                }
                f.write(json.dumps(row) + "\n")

        accepted += 1

    log.info(f"Ingest complete. accepted={accepted}, rejected={rejected}, exceptions_csv={EXCEPTIONS_CSV}")
    log_progress(task, "END", f"accepted={accepted}; rejected={rejected}")
    print(json.dumps({
        "accepted": accepted,
        "rejected": rejected,
        "exceptions_report": EXCEPTIONS_CSV if Path(EXCEPTIONS_CSV).exists() else None,
        "processed_dir": PROCESSED_DIR
    }, indent=2))

if __name__ == "__main__":
    run_ingest()
