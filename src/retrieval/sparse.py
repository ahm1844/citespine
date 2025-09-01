from __future__ import annotations
from typing import Dict, List
from sqlalchemy import text
from sqlalchemy.orm import Session
from ..common.config import SETTINGS
from .synonyms import expand_for_sparse

_EXPR = "to_tsvector('english', coalesce(text, ''))"

def sparse_search(session: Session, qtext: str, filters_sql: str, params: Dict, k: int) -> List[Dict]:
    """Expression-based FTS (matches index, if present)"""
    # Expand query only if enabled; otherwise use raw qtext
    qfts = expand_for_sparse(qtext) if SETTINGS.SYN_EXPAND_ENABLE else qtext
    stmt = text(f"""
        SELECT chunk_id, source_id, text, section_path, page_start, page_end,
               framework, jurisdiction, doc_type, authority_level, effective_date, version,
               ts_rank_cd({_EXPR}, websearch_to_tsquery('english', :qfts)) AS ts_rank
        FROM chunks
        WHERE 1=1 {filters_sql}
          AND {_EXPR} @@ websearch_to_tsquery('english', :qfts)
        ORDER BY ts_rank DESC
        LIMIT :k
    """)
    rows = session.execute(stmt, {**params, "qfts": qfts, "k": k}).mappings().all()
    return [dict(r) for r in rows]
