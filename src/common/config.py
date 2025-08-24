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

SETTINGS = Settings()
