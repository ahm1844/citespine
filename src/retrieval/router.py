"""Backend router: pgvector (default) or Pinecone, with text hydration fallback."""
from typing import Dict, List
from sqlalchemy.orm import Session
from ..common.config import SETTINGS
from ..embedding.provider import EmbeddingProvider
from .retriever import retrieve as retrieve_pg
from .hybrid import hybrid_retrieve
from ..common.logging import get_logger
from opentelemetry import trace

log = get_logger("retrieval/router")
tr = trace.get_tracer("citespine")

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
    with tr.start_as_current_span("retrieve.pre_filters"):
        # metadata filter preparation happens here
        processed_filters = filters or {}
    
    if SETTINGS.VECTOR_BACKEND == "pinecone":
        with tr.start_as_current_span("retrieve.vector_search"):
            qvec = EmbeddingProvider.embed_query(query_text)
            store = _get_pinecone_store()
            hits = store.query(qvec, top_k or SETTINGS.TOP_K, processed_filters)
        _hydrate_texts_from_pg(session, hits)
        return hits
    
    # pgvector path
    if SETTINGS.HYBRID_ENABLE:
        with tr.start_as_current_span("retrieve.hybrid_search"):
            return hybrid_retrieve(session, query_text, processed_filters, top_k or SETTINGS.TOP_K)
    
    # default dense-only (with optional rerank)
    final_k = top_k or SETTINGS.TOP_K
    candidate_k = SETTINGS.RERANK_CANDIDATES if SETTINGS.RERANK_ENABLE else final_k
    
    with tr.start_as_current_span("retrieve.vector_search"):
        hits = retrieve_pg(session, query_text, processed_filters, top_k=candidate_k, probes=probes)
    
    if SETTINGS.RERANK_ENABLE:
        with tr.start_as_current_span("retrieve.rerank"):
            from .rerank import rerank
            return rerank(query_text, hits, SETTINGS.RERANK_MODEL, final_k)
    
    return hits
