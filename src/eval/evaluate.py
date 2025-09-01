"""Run seed set retrieval and print metrics + write manifest."""
import json
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
from ..db.session import get_session
from ..retrieval.retriever import retrieve
from ..common.constants import SEED_QUESTIONS_JSONL, EVAL_DIR
from ..common.logging import get_logger
from ..obs.manifest import write_manifest
from .metrics import recall_at_k

log = get_logger("eval")

def _load_seed():
    p = Path(SEED_QUESTIONS_JSONL)
    if not p.exists():
        raise FileNotFoundError(f"Seed file missing: {SEED_QUESTIONS_JSONL}")
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

def evaluate():
    session: Session = get_session()
    seeds = _load_seed()
    preds = []
    golds = []
    for s in seeds:
        res = retrieve(session, s["q"], s.get("filters", {}), top_k=10, probes=15)
        preds.append([r["chunk_id"] for r in res])
        golds.append(s.get("gold_chunks", []))

    r10 = recall_at_k(preds, golds, 10)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    outdir = Path(EVAL_DIR) / ts
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "metrics.json").write_text(json.dumps({"recall@10": r10}, indent=2), encoding="utf-8")
    (outdir / "predictions.json").write_text(json.dumps(preds, indent=2), encoding="utf-8")

    manifest_path = write_manifest("eval", {"recall@10": r10, "seed_count": len(seeds)})
    print(json.dumps({"recall@10": r10, "seed_count": len(seeds), "manifest": manifest_path}, indent=2))

if __name__ == "__main__":
    evaluate()
