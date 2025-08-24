"""Data Access helpers for Documents and Chunks."""
from typing import Iterable, Sequence, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from .models import Document, Chunk
from ..common.logging import get_logger
from ..common.constants import EMBED_DIM

log = get_logger("db/dao")

def upsert_document(session: Session, d: dict) -> Document:
    doc = session.get(Document, d["source_id"])
    if not doc:
        doc = Document(**d)
        session.add(doc)
    else:
        for k, v in d.items():
            setattr(doc, k, v)
    return doc

def upsert_chunks(session: Session, chunks: Iterable[dict]) -> int:
    count = 0
    for r in chunks:
        ch = session.get(Chunk, r["chunk_id"])
        if not ch:
            ch = Chunk(**r)
            session.add(ch)
            count += 1
    return count

def create_ivfflat_index_if_missing(session: Session):
    """Create ANN index for cosine distance (vector_cosine_ops) if not present."""
    sql = """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'idx_chunks_embedding_cosine'
        ) THEN
            CREATE INDEX idx_chunks_embedding_cosine
            ON chunks USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
        END IF;
    END$$;
    """
    session.execute(text(sql))
    session.commit()
    log.info("IVFFLAT cosine index ensured on chunks.embedding.")

def ann_search(session: Session, qvec: Sequence[float], filters_sql: str, params: dict, top_k: int):
    """Return rows ordered by cosine distance using pgvector <=> operator."""
    # Note: we assume embedding vectors are normalized (cosine)
    sql = f"""
    SELECT chunk_id, source_id, text, section_path, page_start, page_end,
           framework, jurisdiction, doc_type, authority_level, effective_date, version,
           (embedding <=> :qvec) AS distance
    FROM chunks
    WHERE 1=1 {filters_sql}
    ORDER BY embedding <=> :qvec
    LIMIT :top_k
    """
    full_params = {**params, "qvec": list(qvec), "top_k": top_k}
    rows = session.execute(text(sql), full_params).mappings().all()
    return [dict(r) for r in rows]
