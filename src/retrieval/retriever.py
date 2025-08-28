"""High-level retrieval API: embed query → filter-first ANN search."""
from sqlalchemy.orm import Session
from typing import Dict, List
from ..embedding.provider import EmbeddingProvider
from ..db.dao import ann_search
from .filters import build_filters
from ..common.config import SETTINGS

def retrieve(session: Session, query_text: str, filters: Dict, top_k: int | None = None, probes: int = 10) -> List[Dict]:
    qvec = EmbeddingProvider.embed_query(query_text)
    sql, params = build_filters(filters)
    k = top_k or SETTINGS.TOP_K
    return ann_search(session, qvec, sql, params, k, probes=probes)
