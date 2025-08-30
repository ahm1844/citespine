"""
Pinecone Upsert Loader for CiteSpine
------------------------------------

Reads processed JSONL chunks and upserts embeddings + full metadata into Pinecone.

Usage (inside Docker):
  docker compose run --rm api python -m src.tools.pinecone_upsert \
    --processed-dir data/processed \
    --namespace default \
    --batch-size 200 \
    --max-chunks -1 \
    --create-index false

Notes:
- Embeds with sentence-transformers/all-MiniLM-L6-v2 (dim=384).
- ID = chunk_id. Upsert is idempotent (overwrites).
- Keeps 'text' in metadata so Pinecone-only deployments still return evidence.
- in our project with the client, we are gonna use Pinecone... for our project, we will use pgvector.
"""
from __future__ import annotations
import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Iterable, List, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from tqdm import tqdm

from ..common.logging import get_logger
from ..common.constants import PROCESSED_DIR
from ..common.config import SETTINGS
from ..obs.manifest import write_manifest
from ..embedding.provider import EmbeddingProvider

log = get_logger("tools/pinecone_upsert")

# Pinecone client (v3)
try:
    from pinecone import Pinecone, ServerlessSpec
except Exception as e:
    Pinecone = None
    ServerlessSpec = None

EMBED_DIM = 384
TEXT_META_LIMIT = 8000  # be conservative with metadata payload size

@dataclass
class UpsertStats:
    total_vectors: int = 0
    batches: int = 0
    failed_batches: int = 0
    failed_ids: List[str] = None

    def __post_init__(self):
        if self.failed_ids is None:
            self.failed_ids = []

def _iter_jsonl_files(processed_dir: Path) -> List[Path]:
    return sorted(processed_dir.glob("*.jsonl"))

def _iter_rows(files: List[Path]) -> Iterable[Dict[str, Any]]:
    for jf in files:
        with jf.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except Exception as e:
                    log.warning(f"Skipping invalid JSON line in {jf.name}: {e}")

def _prep_metadata(r: Dict[str, Any]) -> Dict[str, Any]:
    text = (r.get("text") or "")[:TEXT_META_LIMIT]
    return {
        "source_id": r.get("source_id", ""),
        "text": text,
        "section_path": r.get("section_path", ""),
        "page_start": r.get("page_start", 0),
        "page_end": r.get("page_end", 0),
        "framework": r.get("framework", ""),
        "jurisdiction": r.get("jurisdiction", ""),
        "doc_type": r.get("doc_type", ""),
        "authority_level": r.get("authority_level", ""),
        "effective_date": r.get("effective_date", ""),
        "version": r.get("version", "")
    }

def _batched(iterable: Iterable[Any], n: int) -> Iterable[List[Any]]:
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= n:
            yield batch
            batch = []
    if batch:
        yield batch

def _ensure_index(pc: "Pinecone", index_name: str) -> None:
    # Only attempt creation if flagged
    if not SETTINGS.PINECONE_CREATE_INDEX:
        return
    names = [i["name"] if isinstance(i, dict) else getattr(i, "name", None) for i in pc.list_indexes()]
    if index_name in names:
        return
    if ServerlessSpec is None:
        raise RuntimeError("pinecone-client ServerlessSpec not available; upgrade client or create index manually.")
    log.info(f"Creating Pinecone index '{index_name}' dim={EMBED_DIM} metric=cosine in {SETTINGS.PINECONE_CLOUD}/{SETTINGS.PINECONE_REGION}")
    pc.create_index(
        name=index_name,
        dimension=EMBED_DIM,
        metric="cosine",
        spec=ServerlessSpec(cloud=SETTINGS.PINECONE_CLOUD, region=SETTINGS.PINECONE_REGION)
    )

@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    retry=retry_if_exception_type(Exception)
)
def _upsert_batch(index, vecs: List[Dict[str, Any]], namespace: str):
    index.upsert(vectors=vecs, namespace=namespace)

def upsert(processed_dir: str, namespace: str, batch_size: int, max_chunks: int) -> Dict[str, Any]:
    if Pinecone is None:
        raise RuntimeError("pinecone-client is not installed. Set VECTOR_BACKEND=pgvector or install pinecone-client.")

    pc = Pinecone(api_key=SETTINGS.PINECONE_API_KEY)
    index = pc.Index(SETTINGS.PINECONE_INDEX_NAME, host=SETTINGS.PINECONE_HOST or None)
    _ensure_index(pc, SETTINGS.PINECONE_INDEX_NAME)

    files = _iter_jsonl_files(Path(processed_dir))
    total_rows = 0
    stats = UpsertStats()

    # Stream all rows (optionally limited)
    rows_iter = _iter_rows(files)
    if max_chunks and max_chunks > 0:
        from itertools import islice
        rows_iter = islice(rows_iter, max_chunks)

    # Process in embedding batches
    for batch_rows in tqdm(_batched(rows_iter, batch_size), desc="Upserting to Pinecone"):
        # Prepare texts and ids
        ids = [r["chunk_id"] for r in batch_rows]
        texts = [r["text"] for r in batch_rows]
        metas = [_prep_metadata(r) for r in batch_rows]

        # Embed
        vecs = EmbeddingProvider.embed_texts(texts)  # ndarray [B, 384]
        # Build vectors payload
        upsert_vecs = [
            {"id": id_, "values": vec.tolist(), "metadata": meta}
            for id_, vec, meta in zip(ids, vecs, metas)
        ]

        try:
            _upsert_batch(index, upsert_vecs, namespace=namespace)
        except Exception as e:
            log.error(f"Upsert batch failed: {e}")
            stats.failed_batches += 1
            stats.failed_ids.extend(ids)
            continue

        stats.total_vectors += len(upsert_vecs)
        stats.batches += 1
        total_rows += len(upsert_vecs)

    manifest = write_manifest("pinecone_upsert", {
        "index": SETTINGS.PINECONE_INDEX_NAME,
        "namespace": namespace,
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "total_vectors": stats.total_vectors,
        "batches": stats.batches,
        "failed_batches": stats.failed_batches,
        "failed_ids": stats.failed_ids,
    })

    return {
        "index": SETTINGS.PINECONE_INDEX_NAME,
        "namespace": namespace,
        "total_vectors": stats.total_vectors,
        "batches": stats.batches,
        "failed_batches": stats.failed_batches,
        "failed_ids": stats.failed_ids,
        "manifest": manifest
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--processed-dir", default=PROCESSED_DIR)
    ap.add_argument("--namespace", default=SETTINGS.PINECONE_NAMESPACE or "default")
    ap.add_argument("--batch-size", type=int, default=200)
    ap.add_argument("--max-chunks", type=int, default=-1, help="-1 = no limit")
    ap.add_argument("--create-index", type=str, default="false", help="true/false (overrides env)")
    args = ap.parse_args()

    # allow CLI override for create index
    if args.create_index.lower() in ("true","1","yes","y"):
        object.__setattr__(SETTINGS, "PINECONE_CREATE_INDEX", True)

    out = upsert(args.processed_dir, args.namespace, args.batch_size, args.max_chunks)
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
