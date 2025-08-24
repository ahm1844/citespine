"""Build the vector index from processed JSONL files (idempotent)."""
import json
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
from ..common.constants import PROCESSED_DIR, INDEX_MANIFEST_JSON
from ..common.logging import get_logger
from ..common.progress import log_progress
from ..obs.manifest import write_manifest
from ..db.init_db import init_db
from ..db.session import get_session
from ..db.dao import upsert_document, upsert_chunks
from ..embedding.provider import EmbeddingProvider

log = get_logger("index/build")

def _iter_rows():
    proc = Path(PROCESSED_DIR)
    for jf in sorted(proc.glob("*.jsonl")):
        with jf.open(encoding="utf-8") as f:
            for line in f:
                yield json.loads(line)

def build_index():
    task = "INDEX"
    log_progress(task, "START", "Embedding and upserting chunks into pgvector")
    init_db()
    session: Session = get_session()

    # Group rows by source_id for doc upsert and batch embeddings
    by_source: dict[str, list[dict]] = {}
    for r in _iter_rows():
        by_source.setdefault(r["source_id"], []).append(r)

    total_chunks = 0
    for sid, rows in by_source.items():
        doc_fields = {k: rows[0][k] for k in ("source_id","title","doc_type","framework","jurisdiction",
                                              "authority_level","effective_date","version","ingest_ts","source_path")}
        doc_fields["hash"] = sid
        upsert_document(session, doc_fields)

        texts = [r["text"] for r in rows]
        vecs = EmbeddingProvider.embed_texts(texts)
        payload = []
        for r, v in zip(rows, vecs):
            rec = {
                "chunk_id": r["chunk_id"],
                "source_id": r["source_id"],
                "section_path": r["section_path"],
                "text": r["text"],
                "tokens": r["tokens"],
                "page_start": r["page_start"],
                "page_end": r["page_end"],
                "framework": r["framework"],
                "jurisdiction": r["jurisdiction"],
                "doc_type": r["doc_type"],
                "authority_level": r["authority_level"],
                "effective_date": r["effective_date"],
                "version": r["version"],
                "embedding": v.tolist(),
            }
            payload.append(rec)

        total_chunks += upsert_chunks(session, payload)
        session.commit()

    Path(INDEX_MANIFEST_JSON).write_text(json.dumps({
        "created_at": datetime.utcnow().isoformat(),
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "files_indexed": len(by_source),
        "total_chunks": total_chunks
    }, indent=2), encoding="utf-8")

    write_manifest("index_build", {
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "total_chunks": total_chunks
    })
    log_progress(task, "END", f"total_chunks={total_chunks}")
    print(json.dumps({"indexed_files": len(by_source), "total_chunks": total_chunks, "manifest": INDEX_MANIFEST_JSON}, indent=2))

if __name__ == "__main__":
    build_index()
