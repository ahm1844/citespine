"""
Seed Top-K dump for CiteSpine.

Writes a CSV per seed with dense and sparse ranks/scores so you can correct gold labels.
No schema changes and no new dependencies.

Usage examples:
  # Dump all seeds with top-100 candidates (dense+ sparse), probes=15
  docker compose run --rm api python -m src.eval.seed_dump --top-k 100 --probes 15

  # Dump a subset
  docker compose run --rm api python -m src.eval.seed_dump --top-k 100 --probes 15 --ids Q001,Q004,Q010
"""
from __future__ import annotations
import csv, json
from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, List, Any
from sqlalchemy.orm import Session

from ..common.constants import SEED_QUESTIONS_JSONL
from ..common.logging import get_logger
from ..db.session import get_session
from ..retrieval.filters import build_filters
from ..embedding.provider import EmbeddingProvider
from ..db.dao import ann_search
from ..retrieval.sparse import sparse_search
from ..common.config import SETTINGS

log = get_logger("eval/seed_dump")

OUT_DIR = Path("data/eval/seed_dump")

def _load_seeds() -> List[Dict[str, Any]]:
    p = Path(SEED_QUESTIONS_JSONL)
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

def _truncate(s: str, n: int = 240) -> str:
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[:n-1] + "…"

def dump(top_k: int, probes: int, ids: List[str] | None) -> Dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    seeds = _load_seeds()
    if ids:
        allow = set([x.strip() for x in ids if x.strip()])
        seeds = [s for s in seeds if s.get("id") in allow]

    session: Session = get_session()
    total = 0
    for s in seeds:
        qid = s["id"]
        q = s["q"]
        filters = s.get("filters", {})
        gold = set(s.get("gold_chunks") or [])
        sql, params = build_filters(filters or {})

        # Dense candidates
        qvec = EmbeddingProvider.embed_query(q)
        dense_hits = ann_search(session, qvec, sql, params, top_k, probes=probes)
        d_rank = {h["chunk_id"]: i+1 for i, h in enumerate(dense_hits)}
        d_dist = {h["chunk_id"]: float(h.get("distance", 0.0)) for h in dense_hits}

        # Sparse candidates (expression-based FTS; index optional)
        sparse_hits = sparse_search(session, q, sql, params, top_k)
        s_rank = {h["chunk_id"]: i+1 for i, h in enumerate(sparse_hits)}
        s_ts   = {h["chunk_id"]: float(h.get("ts_rank", 0.0)) for h in sparse_hits}

        # Union of candidate ids
        ids_union = list(dict.fromkeys([*d_rank.keys(), *s_rank.keys()]))  # preserve dense order first

        outp = OUT_DIR / f"seed_{qid}.csv"
        with outp.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "qid","q","framework","jurisdiction","as_of","chunk_id",
                "rank_dense","distance","rank_sparse","ts_rank",
                "is_gold","section_path","page_span","snippet"
            ])
            for cid in ids_union:
                # find representative row (prefer dense row)
                row = next((h for h in dense_hits if h["chunk_id"] == cid), None) \
                      or next((h for h in sparse_hits if h["chunk_id"] == cid), None)
                w.writerow([
                    qid, _truncate(q, 200),
                    filters.get("framework",""), filters.get("jurisdiction",""), filters.get("as_of",""),
                    cid,
                    d_rank.get(cid) or "", d_dist.get(cid) if cid in d_dist else "",
                    s_rank.get(cid) or "", s_ts.get(cid) if cid in s_ts else "",
                    "Y" if cid in gold else "",
                    row.get("section_path",""),
                    f"{row.get('page_start','')}-{row.get('page_end','')}",
                    _truncate(row.get("text",""), 240)
                ])
                total += 1
        log.info(f"Wrote {outp}")

    return {"files": len(seeds), "rows": total}

if __name__ == "__main__":
    ap = ArgumentParser()
    ap.add_argument("--top-k", type=int, default=100)
    ap.add_argument("--probes", type=int, default=15)
    ap.add_argument("--ids", type=str, default="")
    a = ap.parse_args()
    ids = [x for x in a.ids.split(",")] if a.ids else None
    out = dump(a.top_k, a.probes, ids)
    print(out)
