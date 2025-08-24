"""Embedding provider abstraction; defaults to local sentence-transformers."""
from __future__ import annotations
from typing import List, Iterable
import numpy as np
from sentence_transformers import SentenceTransformer
from ..common.constants import EMBED_DIM
from ..common.logging import get_logger

log = get_logger("embedding/provider")

class EmbeddingProvider:
    _model: SentenceTransformer | None = None

    @classmethod
    def _ensure_model(cls):
        if cls._model is None:
            log.info("Loading local embedding model: sentence-transformers/all-MiniLM-L6-v2")
            cls._model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    @classmethod
    def embed_texts(cls, texts: Iterable[str]) -> np.ndarray:
        cls._ensure_model()
        vecs = cls._model.encode(list(texts), normalize_embeddings=True)
        if vecs.shape[1] != EMBED_DIM:
            raise ValueError(f"Expected dim {EMBED_DIM}, got {vecs.shape[1]}")
        return vecs

    @classmethod
    def embed_query(cls, text: str) -> np.ndarray:
        return cls.embed_texts([text])[0]
