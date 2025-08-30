"""Pinecone adapter shim for CiteSpine.

- Mirrors the minimal query interface our retrieval layer needs.
- Assumes Pinecone vectors indexed with metadata containing at least:
  { chunk_id=id, source_id, framework, jurisdiction, doc_type, authority_level,
    effective_date (YYYY-MM-DD), version, section_path, page_start, page_end,
    text (optional but recommended) }

NOTE: in our project with the client, we are gonna use Pinecone... for our project, we will use pgvector.
"""
from __future__ import annotations
from typing import Dict, List, Sequence, Any
from dataclasses import dataclass
from datetime import date
from ..common.config import SETTINGS
from ..common.logging import get_logger

log = get_logger("vectorstore/pinecone")

try:
    from pinecone import Pinecone
except Exception:
    Pinecone = None  # lazy import guard

def _parse_iso(d: str | None) -> date | None:
    if not d:
        return None
    try:
        return date.fromisoformat(d)
    except Exception:
        return None

@dataclass
class PineconeStore:
    api_key: str
    index_name: str
    host: str | None = None
    namespace: str = "default"

    def __post_init__(self):
        if Pinecone is None:
            raise RuntimeError("pinecone-client not installed. Set VECTOR_BACKEND=pgvector or install pinecone-client.")
        self.pc = Pinecone(api_key=self.api_key)
        self.index = self.pc.Index(self.index_name, host=self.host) if self.host else self.pc.Index(self.index_name)
        log.info(f"Pinecone index ready: {self.index_name} ns={self.namespace}")

    @staticmethod
    def _translate_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
        """Translate our filters into Pinecone filter grammar. ISO dates compare lexicographically."""
        out: Dict[str, Any] = {}
        for k in ("framework", "jurisdiction", "doc_type", "authority_level"):
            if k in filters and filters[k]:
                out[k] = {"$eq": filters[k]}
        if "as_of" in filters and filters["as_of"]:
            out["effective_date"] = {"$lte": filters["as_of"]}
        return out

    def query(self, qvec: Sequence[float], top_k: int, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        pc_filter = self._translate_filters(filters or {})
        res = self.index.query(
            vector=list(qvec),
            top_k=top_k,
            include_metadata=True,
            filter=pc_filter,
            namespace=self.namespace
        )
        rows: List[Dict[str, Any]] = []
        for m in getattr(res, "matches", []) or []:
            md = m.metadata or {}
            rows.append({
                "chunk_id": m.id,
                "source_id": md.get("source_id", ""),
                "text": md.get("text", ""),  # may be absent; router hydrates from pg later
                "section_path": md.get("section_path", ""),
                "page_start": md.get("page_start", 0),
                "page_end": md.get("page_end", 0),
                "framework": md.get("framework", ""),
                "jurisdiction": md.get("jurisdiction", ""),
                "doc_type": md.get("doc_type", ""),
                "authority_level": md.get("authority_level", ""),
                "effective_date": md.get("effective_date", ""),
                "version": md.get("version", ""),
                # Pinecone score is similarity; convert to distance ~ (1 - sim)
                "distance": 1.0 - float(m.score) if getattr(m, "score", None) is not None else 0.0
            })

        # Secondary sort: newest effective_date tiebreak (preserve semantic order first)
        rows.sort(key=lambda r: (r.get("distance", 1e9), -(_parse_iso(r.get("effective_date")) or date.min).toordinal()))
        return rows
