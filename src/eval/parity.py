"""Parity harness: compare pgvector vs Pinecone retrieval on the seed set.
Writes a JSON report and a manifest entry. Run after setting Pinecone env if you want both.
Usage:
  docker compose run --rm api python -m src.eval.parity --top-k 10 --probes 15
"""
from __future__ import annotations
import json
from pathlib import Path
from argparse import ArgumentParser
from typing import Dict, List, Tuple, Any, Set
from datetime import datetime

from sqlalchemy.orm import Session

from ..common.constants import SEED_QUESTIONS_JSONL, EVAL_DIR
from ..common.config import SETTINGS
from ..common.logging import get_logger
from ..obs.manifest import write_manifest
from ..db.session import get_session

from ..retrieval.retriever import retrieve as retrieve_pg
from ..embedding.provider import EmbeddingProvider

log = get_logger("eval/parity")

def _load_seeds() -> List[Dict[str, Any]]:
    p = Path(SEED_QUESTIONS_JSONL)
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    return rows

def _pc_query(qvec, top_k: int, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    from ..vectorstore.pinecone_store import PineconeStore
    store = PineconeStore(
        api_key=SETTINGS.PINECONE_API_KEY,
        index_name=SETTINGS.PINECONE_INDEX_NAME,
        host=SETTINGS.PINECONE_HOST or None,
        namespace=SETTINGS.PINECONE_NAMESPACE or "default",
    )
    return store.query(qvec, top_k, filters or {})

def _topk_ids(rows: List[Dict[str, Any]], k: int) -> List[str]:
    return [r["chunk_id"] for r in rows[:k]]

def _overlap(a: List[str], b: List[str]) -> Tuple[int, float, float]:
    sa, sb = set(a), set(b)
    inter = len(sa & sb)
    jacc = inter / max(1, len(sa | sb))
    cov  = inter / max(1, len(a))
    return inter, jacc, cov

def run(top_k: int, probes: int) -> Dict[str, Any]:
    seeds = _load_seeds()
    session: Session = get_session()
    results = []
    any_pinecone = SETTINGS.VECTOR_BACKEND == "pinecone" or bool(SETTINGS.PINECONE_API_KEY and SETTINGS.PINECONE_INDEX_NAME)

    for s in seeds:
        q = s["q"]
        filters = s.get("filters", {})
        # pgvector path
        pg_hits = retrieve_pg(session, q, filters, top_k=top_k, probes=probes)
        pg_ids = _topk_ids(pg_hits, top_k)

        row = {"id": s["id"], "q": q, "pg_top_k": pg_ids}

        if any_pinecone:
            qvec = EmbeddingProvider.embed_query(q)
            pc_hits = _pc_query(qvec, top_k, filters)
            pc_ids = _topk_ids(pc_hits, top_k)
            inter, jacc, cov = _overlap(pg_ids, pc_ids)
            row.update({
                "pc_top_k": pc_ids,
                "overlap": inter,
                "jaccard": round(jacc, 3),
                "coverage_pg_in_pc": round(cov, 3)
            })
        results.append(row)

    summary = {}
    if any_pinecone:
        js = [r["jaccard"] for r in results if "jaccard" in r]
        cs = [r["coverage_pg_in_pc"] for r in results if "coverage_pg_in_pc" in r]
        summary = {
            "avg_jaccard": round(sum(js) / max(1, len(js)), 3),
            "avg_coverage_pg_in_pc": round(sum(cs) / max(1, len(cs)), 3)
        }

    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    outdir = Path(EVAL_DIR) / f"parity_{ts}"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "report.json").write_text(json.dumps({"top_k": top_k, "probes": probes, "results": results, "summary": summary}, indent=2), encoding="utf-8")

    manifest = write_manifest("parity", {"top_k": top_k, "probes": probes, "summary": summary})
    return {"report_dir": str(outdir), "manifest": manifest, "summary": summary}

if __name__ == "__main__":
    ap = ArgumentParser()
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--probes", type=int, default=10)
    args = ap.parse_args()
    out = run(args.top_k, args.probes)
    print(json.dumps(out, indent=2))
