from __future__ import annotations
from typing import Dict, List
from math import inf
from sqlalchemy.orm import Session
from .filters import build_filters
from ..embedding.provider import EmbeddingProvider
from ..db.dao import ann_search
from .sparse import sparse_search
from ..common.config import SETTINGS

def _minmax(values, invert=False):
    """Min-max normalize values, optionally invert for distance scores"""
    if not values:
        return {}
    vmin, vmax = min(values.values()), max(values.values())
    denom = (vmax - vmin) or 1e-9
    out = {}
    for k, v in values.items():
        norm = (v - vmin) / denom
        out[k] = (1.0 - norm) if invert else norm
    return out

def hybrid_retrieve(session: Session, query_text: str, filters: Dict, top_k: int) -> List[Dict]:
    """Hybrid sparse+dense retrieval with normalized weighted blending"""
    # 1) Build filters + retrieve candidates from both retrievers
    sql, params = build_filters(filters or {})
    qvec = EmbeddingProvider.embed_query(query_text)

    dense_hits = ann_search(session, qvec, sql, params, SETTINGS.HYBRID_K_DENSE, probes=10)
    sparse_hits = sparse_search(session, query_text, sql, params, SETTINGS.HYBRID_K_SPARSE)

    # 2) Collect scores
    d_dist = {h["chunk_id"]: float(h.get("distance", inf)) for h in dense_hits}
    s_rank = {h["chunk_id"]: float(h.get("ts_rank", 0.0)) for h in sparse_hits}

    # 3) Normalize: distance (lower is better) -> invert after min-max;
    #    ts_rank (higher is better) -> min-max
    d_norm = _minmax(d_dist, invert=True)  # now higher is better for dense
    s_norm = _minmax(s_rank, invert=False)

    # 4) Blend with weights (missing scores default to 0)
    alpha, beta = SETTINGS.HYBRID_W_DENSE, SETTINGS.HYBRID_W_SPARSE
    all_ids = set(d_dist) | set(s_rank)
    merged: Dict[str, Dict] = {}

    # Keep one representative row per id (prefer dense row for richer fields)
    ref = {}
    for h in dense_hits:
        ref[h["chunk_id"]] = h
    for h in sparse_hits:
        ref.setdefault(h["chunk_id"], h)

    for cid in all_ids:
        score = alpha * d_norm.get(cid, 0.0) + beta * s_norm.get(cid, 0.0)
        r = dict(ref[cid])
        r["_hybrid_score"] = score
        merged[cid] = r

    # 5) Sort by blended score desc and return top_k
    ranked = sorted(merged.values(), key=lambda x: x.get("_hybrid_score", 0.0), reverse=True)
    return ranked[:top_k]
