"""Seed gold labeling helper.

Usage:
  python -m src.eval.label add Q001 <CHUNK_ID>
  python -m src.eval.label remove Q001 <CHUNK_ID>
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from ..common.constants import SEED_QUESTIONS_JSONL
from ..common.logging import get_logger

log = get_logger("eval/label")

def _load() -> list[dict]:
    p = Path(SEED_QUESTIONS_JSONL)
    if not p.exists():
        raise FileNotFoundError(f"Seed file missing: {SEED_QUESTIONS_JSONL}")
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

def _save(rows: list[dict]) -> None:
    p = Path(SEED_QUESTIONS_JSONL)
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

def add_label(qid: str, chunk_id: str):
    rows = _load()
    for r in rows:
        if r.get("id") == qid:
            gold = list(dict.fromkeys((r.get("gold_chunks") or []) + [chunk_id]))
            r["gold_chunks"] = gold
            _save(rows)
            log.info(f"Added gold chunk {chunk_id} to {qid}")
            return
    raise ValueError(f"Question id not found: {qid}")

def remove_label(qid: str, chunk_id: str):
    rows = _load()
    for r in rows:
        if r.get("id") == qid:
            r["gold_chunks"] = [c for c in (r.get("gold_chunks") or []) if c != chunk_id]
            _save(rows)
            log.info(f"Removed gold chunk {chunk_id} from {qid}")
            return
    raise ValueError(f"Question id not found: {qid}")

if __name__ == "__main__":
    if len(sys.argv) < 4 or sys.argv[1] not in ("add", "remove"):
        print(__doc__)
        sys.exit(2)
    cmd, qid, cid = sys.argv[1], sys.argv[2], sys.argv[3]
    (add_label if cmd == "add" else remove_label)(qid, cid)
