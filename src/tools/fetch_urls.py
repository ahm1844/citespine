"""
Download PDFs from a URLs file into data/raw/ and append strict manifest rows.

Usage:
  docker compose run --rm api python -m src.tools.fetch_urls \
    --urls-file data/raw/urls.txt \
    --framework Other \
    --jurisdiction US \
    --doc-type standard \
    --authority-level authoritative \
    --effective-date 2023-12-31 \
    --version 2023 \
    [--title-prefix "PCAOB AS"] \
    [--workers 4]

Notes:
- Validates metadata against config/metadata.yml (allowed + synonyms).
- Appends to data/raw/manifest.csv with header guard, idempotent on filename.
- Skips existing files by name; verifies PDF magic when possible.
"""
from __future__ import annotations
import argparse
import csv
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Any, List
import re
import requests
from requests import Session
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from tqdm import tqdm

from ..common.constants import RAW_DIR
from ..common.config import SETTINGS
from ..common.logging import get_logger
from ..ingest.metadata import load_vocab, normalize_record

log = get_logger("tools/fetch_urls")

RAW = Path(RAW_DIR)
MANIFEST = RAW / "manifest.csv"
VOCAB = Path("config/metadata.yml")

PDF_MAGIC = b"%PDF"

def _sanitize_filename(s: str) -> str:
    s = s.strip().replace(" ", "_")
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s)
    return s[:255]

def _filename_from_url(url: str) -> str:
    tail = url.split("?")[0].rstrip("/").split("/")[-1] or "download.pdf"
    if not tail.lower().endswith(".pdf"):
        tail = tail + ".pdf"
    return _sanitize_filename(tail)

def _ensure_manifest_header():
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    if not MANIFEST.exists() or MANIFEST.stat().st_size == 0:
        with MANIFEST.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["filename","title","doc_type","framework","jurisdiction","authority_level","effective_date","version"])

def _manifest_row_exists(filename: str) -> bool:
    if not MANIFEST.exists():
        return False
    with MANIFEST.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("filename") == filename:
                return True
    return False

@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((requests.RequestException,))
)
def _download(session: Session, url: str, dest: Path, timeout: int) -> None:
    headers = {"User-Agent": SETTINGS.SEC_USER_AGENT}
    with session.get(url, headers=headers, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with tmp.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 64):
                if chunk:
                    f.write(chunk)
        tmp.replace(dest)

def _is_pdf(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            return f.read(4) == PDF_MAGIC
    except Exception:
        return False

def _append_manifest_row(row: Dict[str, str]) -> None:
    _ensure_manifest_header()
    with MANIFEST.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([row["filename"], row["title"], row["doc_type"], row["framework"],
                    row["jurisdiction"], row["authority_level"], row["effective_date"], row["version"]])

def validate_metadata_or_die(row: Dict[str, str]) -> Dict[str, Any]:
    vocab = load_vocab(VOCAB)
    norm, errs = normalize_record(row, vocab)
    if errs:
        msgs = [f'{k}="{v.get("provided")}" -> suggest "{v.get("suggestion")}"' for k, v in errs.items()]
        raise ValueError("Invalid metadata: " + "; ".join(msgs))
    return norm

def run(urls: List[str], meta: Dict[str, str], workers: int, timeout: int, title_prefix: str | None):
    RAW.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.trust_env = True  # respect system proxies if any

    tasks = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        for url in urls:
            url = url.strip()
            if not url:
                continue
            fname = _filename_from_url(url)
            dest = RAW / fname
            if dest.exists() and dest.stat().st_size > 0:
                # best-effort magic check; skip re-download
                if not _is_pdf(dest):
                    log.warning(f"Existing file not recognized as PDF, re-downloading: {fname}")
                else:
                    # ensure manifest row exists
                    if not _manifest_row_exists(fname):
                        row = {**meta}
                        row["filename"] = fname
                        row["title"] = row.get("title") or fname
                        validate_metadata_or_die(row)
                        _append_manifest_row(row)
                    continue
            tasks.append(ex.submit(_download, session, url, dest, timeout))

        for _ in tqdm(as_completed(tasks), total=len(tasks), desc="Downloading PDFs"):
            pass

    # Append manifest rows
    for url in urls:
        url = url.strip()
        if not url:
            continue
        fname = _filename_from_url(url)
        dest = RAW / fname
        if not dest.exists() or dest.stat().st_size == 0 or not _is_pdf(dest):
            log.warning(f"Skipping manifest entry (missing or non-PDF): {fname}")
            continue
        if _manifest_row_exists(fname):
            continue
        row = {**meta}
        row["filename"] = fname
        row["title"] = (title_prefix + " " if title_prefix else "") + Path(fname).stem.replace("_", " ")
        validate_metadata_or_die(row)
        _append_manifest_row(row)
    log.info("Download + manifest append complete.")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--urls-file", required=True)
    p.add_argument("--framework", required=True, choices=["IFRS","US_GAAP","Other"])
    p.add_argument("--jurisdiction", required=True, choices=["Global","US","EU","UK","Other"])
    p.add_argument("--doc-type", required=True, choices=["standard","filing","policy","memo","disclosure"])
    p.add_argument("--authority-level", required=True, choices=["authoritative","interpretive","internal_policy"])
    p.add_argument("--effective-date", required=True, help="YYYY-MM-DD")
    p.add_argument("--version", required=True)
    p.add_argument("--title-prefix", default="")
    p.add_argument("--workers", type=int, default=SETTINGS.DOWNLOAD_WORKERS)
    p.add_argument("--timeout", type=int, default=SETTINGS.DOWNLOAD_TIMEOUT)
    args = p.parse_args()

    urls = [u.strip() for u in Path(args.urls_file).read_text(encoding="utf-8").splitlines() if u.strip()]
    meta = {
        "title": "",  # set later per file
        "doc_type": args.doc_type,
        "framework": args.framework,
        "jurisdiction": args.jurisdiction,
        "authority_level": args.authority_level,
        "effective_date": args.effective_date,
        "version": args.version
    }
    run(urls, meta, args.workers, args.timeout, args.title_prefix or None)

if __name__ == "__main__":
    main()
