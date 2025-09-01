"""
Seed diagnostics for CiteSpine.
- Verifies each seed's gold chunk IDs exist
- Checks whether seed filters would include the gold chunks
- Retrieves top-K=50 candidates and reports if/where gold appears
- Prints actionable causes per seed

Usage:
  docker compose run --rm api python -m src.eval.seed_diag --top-k 50 --probes 15
"""
from __future__ import annotations
import json
from argparse import ArgumentParser
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..common.constants import SEED_QUESTIONS_JSONL
from ..common.logging import get_logger
from ..db.session import get_session
from ..db.models import Chunk
from ..retrieval.retriever import retrieve as retrieve_pg
from ..retrieval.filters import build_filters
from ..embedding.provider import EmbeddingProvider

log = get_logger("eval/seed_diag")

def _load_seeds() -> List[Dict[str, Any]]:
    p = Path(SEED_QUESTIONS_JSONL)
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

def _as_date(s: str | None) -> date | None:
    if not s: return None
    try:
        return date.fromisoformat(s)
    except Exception:
        return None

def _exists(session: Session, chunk_id: str) -> Dict[str, Any] | None:
    row = session.execute(
        select(
            Chunk.chunk_id, Chunk.source_id, Chunk.framework, Chunk.jurisdiction,
            Chunk.doc_type, Chunk.authority_level, Chunk.effective_date, Chunk.version
        ).where(Chunk.chunk_id == chunk_id)
    ).first()
    if not row: return None
    r = row._asdict() if hasattr(row, "_asdict") else dict(row)
    return r

def _passes_filters(meta: Dict[str, Any], filters: Dict[str, Any]) -> Tuple[bool, List[str]]:
    issues = []
    for k in ("framework","jurisdiction","doc_type","authority_level"):
        fv = filters.get(k)
        if fv and meta.get(k) != fv:
            issues.append(f'{k} mismatch: gold="{meta.get(k)}" vs filter="{fv}"')
    # as_of rule: effective_date <= as_of
    as_of = _as_date(filters.get("as_of"))
    if as_of:
        eff = meta.get("effective_date")
        if hasattr(eff, "toordinal"):  # already a date
            eff_d = eff
        else:
            eff_d = _as_date(str(eff)) if eff is not None else None
        if eff_d and eff_d > as_of:
            issues.append(f'effective_date {eff_d.isoformat()} > as_of {as_of.isoformat()}')
    return (len(issues) == 0), issues

def _rank_in_hits(hits: List[Dict[str,Any]], gold_ids: List[str]) -> Tuple[int | None, str | None]:
    id_to_rank = {h["chunk_id"]: i+1 for i,h in enumerate(hits)}
    for gid in gold_ids:
        if gid in id_to_rank:
            return id_to_rank[gid], gid
    return None, None

def run(top_k: int, probes: int) -> Dict[str, Any]:
    session: Session = get_session()
    seeds = _load_seeds()
    report = []

    for s in seeds:
        qid = s["id"]
        q = s["q"]
        filters = s.get("filters", {})
        gold = s.get("gold_chunks") or []

        # Validate golds
        gold_meta = []
        missing = []
        for gid in gold:
            m = _exists(session, gid)
            if not m: missing.append(gid)
            else: gold_meta.append(m)

        # Check filter compatibility for first present gold
        filter_ok = None
        filter_issues = []
        for m in gold_meta:
            ok, issues = _passes_filters(m, filters)
            filter_ok = ok if filter_ok is None else (filter_ok or ok)
            filter_issues.extend([f"{m['chunk_id']}: {x}" for x in issues])

        # Retrieve with top_k (diagnostic uses K=50 by default)
        hits = retrieve_pg(session, q, filters, top_k=top_k, probes=probes)
        rank, which = _rank_in_hits(hits, gold)

        cause = []
        if missing:
            cause.append(f"missing_gold_in_index={len(missing)}")
        if filter_ok is False:
            cause.append("gold_excluded_by_filters")
        if rank is None and not missing and (filter_ok or filter_ok is None):
            cause.append("gold_not_in_topK")

        report.append({
            "id": qid,
            "q": q,
            "filters": filters,
            "gold_count": len(gold),
            "missing_gold": missing,
            "filter_ok": filter_ok,
            "filter_issues": filter_issues,
            "topK": top_k,
            "rank_of_any_gold": rank,
            "gold_id_found": which,
            "cause": ", ".join(cause) if cause else "ok"
        })

    outp = Path("data/eval/seed_diag_report.json")
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps({"results": report}, indent=2), encoding="utf-8")
    print(json.dumps({"written": str(outp), "count": len(report)}, indent=2))
    return {"path": str(outp), "count": len(report)}

if __name__ == "__main__":
    ap = ArgumentParser()
    ap.add_argument("--top-k", type=int, default=50)
    ap.add_argument("--probes", type=int, default=15)
    args = ap.parse_args()
    run(args.top_k, args.probes)
