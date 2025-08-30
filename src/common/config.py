"""Environment & configuration loader (tidy, single source of truth)."""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv(override=True)

@dataclass(frozen=True)
class Settings:
    # Providers
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")  # or openai
    EMBEDDINGS_PROVIDER: str = os.getenv("EMBEDDINGS_PROVIDER", "local")  # or openai

    # Postgres / pgvector
    PG_DSN: str = os.getenv(
        "PG_DSN",
        "postgresql+psycopg://postgres:postgres@postgres:5432/citespine"
    )

    # Defaults / knobs
    AS_OF_DEFAULT: str = os.getenv("AS_OF_DEFAULT", "2023-12-31")
    TOP_K: int = int(os.getenv("TOP_K", "10"))
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "900"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "150"))

    # Optional OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_EMBED_MODEL: str = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

    # Vector backend: "pgvector" (default) or "pinecone"
    VECTOR_BACKEND: str = os.getenv("VECTOR_BACKEND", "pgvector").lower()

    # Pinecone (used only if VECTOR_BACKEND=pinecone)
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "")
    PINECONE_HOST: str = os.getenv("PINECONE_HOST", "")  # optional, some regions require explicit host
    PINECONE_NAMESPACE: str = os.getenv("PINECONE_NAMESPACE", "default")

    SEC_USER_AGENT: str = os.getenv("SEC_USER_AGENT", "CiteSpine/0.1 (contact@example.com)")
    DOWNLOAD_WORKERS: int = int(os.getenv("DOWNLOAD_WORKERS", "4"))
    DOWNLOAD_TIMEOUT: int = int(os.getenv("DOWNLOAD_TIMEOUT", "45"))

    PINECONE_CREATE_INDEX: bool = os.getenv("PINECONE_CREATE_INDEX", "false").lower() == "true"
    PINECONE_CLOUD: str = os.getenv("PINECONE_CLOUD", "aws")
    PINECONE_REGION: str = os.getenv("PINECONE_REGION", "us-east-1")

SETTINGS = Settings()
