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

    # Authentication & Access Control
    INVITE_TOKEN: str = os.getenv("INVITE_TOKEN", "").strip()  # leave blank to disable gating
    COOKIE_DOMAIN: str = os.getenv("COOKIE_DOMAIN", "").strip()  # ".yourdomain.com" or blank for localhost
    API_KEY_HEADER: str = os.getenv("API_KEY_HEADER", "X-Api-Key")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "data/uploads")

    PINECONE_CREATE_INDEX: bool = os.getenv("PINECONE_CREATE_INDEX", "false").lower() == "true"
    PINECONE_CLOUD: str = os.getenv("PINECONE_CLOUD", "aws")
    PINECONE_REGION: str = os.getenv("PINECONE_REGION", "us-east-1")

    # Re-ranking (optional lever for recall improvement) - OFF by default
    RERANK_ENABLE: bool = os.getenv("RERANK_ENABLE", "false").lower() == "true"
    RERANK_MODEL: str = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    RERANK_CANDIDATES: int = int(os.getenv("RERANK_CANDIDATES", "50"))

    # Hybrid retrieval (sparse + dense)
    HYBRID_ENABLE: bool = os.getenv("HYBRID_ENABLE", "false").lower() == "true"
    HYBRID_K_DENSE: int = int(os.getenv("HYBRID_K_DENSE", "100"))   # dense candidate depth
    HYBRID_K_SPARSE: int = int(os.getenv("HYBRID_K_SPARSE", "100")) # sparse candidate depth
    HYBRID_W_DENSE: float = float(os.getenv("HYBRID_W_DENSE", "0.6"))
    HYBRID_W_SPARSE: float = float(os.getenv("HYBRID_W_SPARSE", "0.4"))

    # Sparse query synonym expansion (applies only to FTS path)
    SYN_EXPAND_ENABLE: bool = os.getenv("SYN_EXPAND_ENABLE", "false").lower() == "true"
    SYN_DEBUG_LOG: bool = os.getenv("SYN_DEBUG_LOG", "false").lower() == "true"

    # Demo Mode Configuration
    DEMO_MODE: bool = os.getenv("DEMO_MODE","false").lower() in ("1","true","yes")
    DEMO_RATE_LIMIT_PER_IP: str = os.getenv("DEMO_RATE_LIMIT_PER_IP","20/hour")
    DEMO_MAX_FILE_MB: int = int(os.getenv("DEMO_MAX_FILE_MB","10"))
    DEMO_DELETE_AFTER_MIN: int = int(os.getenv("DEMO_DELETE_AFTER_MIN","60"))
    DEMO_NAMESPACE: str = os.getenv("DEMO_NAMESPACE","demo")
    DEMO_EXPORT_REQUIRE_EMAIL: bool = os.getenv("DEMO_EXPORT_REQUIRE_EMAIL","true").lower() in ("1","true","yes")

SETTINGS = Settings()
