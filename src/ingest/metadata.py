"""Controlled vocabularies, synonym normalization, and exceptions report."""
import csv
import hashlib
from pathlib import Path
from typing import Dict, Any, Tuple
from datetime import date
import yaml
from ..common.constants import EXCEPTIONS_CSV, REQUIRED_DOC_FIELDS

def load_vocab(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))

def compute_source_id(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

def _canon(s: str) -> str:
    return (s or "").strip()

def _is_iso_date(s: str) -> bool:
    try:
        date.fromisoformat((s or "").strip())
        return True
    except Exception:
        return False

def normalize_field(name: str, raw: str, vocab: Dict[str, Any]) -> Tuple[str, str]:
    allowed = set(vocab.get(name, {}).get("allowed", []))
    synonyms = vocab.get(name, {}).get("synonyms", {}) or {}
    v = _canon(raw)
    if not v:
        return "", "REQUIRED"
    if v in synonyms:
        v = synonyms[v]
    if allowed and v not in allowed:
        # return closest suggestion by case-insensitive direct match
        suggestion = next((a for a in allowed if a.lower() == v.lower()), "")
        return "", suggestion or "UNKNOWN"
    return v, ""

def normalize_record(rec: Dict[str, str], vocab: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    out, errors = {}, {}
    for f in REQUIRED_DOC_FIELDS:
        v, s = normalize_field(f, rec.get(f, ""), vocab)
        if not v:
            errors[f] = {"provided": rec.get(f, ""), "suggestion": s}
        else:
            out[f] = v

    # Extra guard: strict ISO date format
    if "effective_date" in out and not _is_iso_date(out["effective_date"]):
        errors["effective_date"] = {"provided": rec.get("effective_date", ""), "suggestion": "YYYY-MM-DD"}
        out.pop("effective_date", None)

    return out, errors

def write_exception_row(filename: str, field: str, provided: str, suggestion: str, reason: str):
    path = Path(EXCEPTIONS_CSV)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = ["filename","field","provided","suggestion","reason"]
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(header)
        w.writerow([filename, field, provided, suggestion, reason])
