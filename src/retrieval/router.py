"""Backend router: pgvector (default) or Pinecone, with text hydration fallback."""
from typing import Dict, List
from sqlalchemy.orm import Session
from ..common.config import SETTINGS
from ..embedding.provider import EmbeddingProvider
from .retriever import retrieve as retrieve_pg
from ..common.logging import get_logger

log = get_logger("retrieval/router")

_pinecone_store = None

def _get_pinecone_store():
    global _pinecone_store
    if _pinecone_store is None:
        from ..vectorstore.pinecone_store import PineconeStore
        _pinecone_store = PineconeStore(
            api_key=SETTINGS.PINECONE_API_KEY,
            index_name=SETTINGS.PINECONE_INDEX_NAME,
            host=SETTINGS.PINECONE_HOST or None,
            namespace=SETTINGS.PINECONE_NAMESPACE or "default"
        )
    return _pinecone_store

def _hydrate_texts_from_pg(session: Session, hits: List[Dict]) -> None:
    """If Pinecone metadata didn't include 'text', fetch from local chunks by chunk_id."""
    missing = [h["chunk_id"] for h in hits if not (h.get("text") or "").strip()]
    if not missing:
        return
    from ..db.dao import get_chunk_text_map
    m = get_chunk_text_map(session, missing)
    for h in hits:
        if not (h.get("text") or "").strip():
            h["text"] = m.get(h["chunk_id"], "")

def retrieve_any(session: Session, query_text: str, filters: Dict, top_k: int | None = None, probes: int = 10) -> List[Dict]:
    if SETTINGS.VECTOR_BACKEND == "pinecone":
        qvec = EmbeddingProvider.embed_query(query_text)
        store = _get_pinecone_store()
        hits = store.query(qvec, top_k or SETTINGS.TOP_K, filters or {})
        _hydrate_texts_from_pg(session, hits)
        return hits
    # default: pgvector
    return retrieve_pg(session, query_text, filters or {}, top_k, probes)
