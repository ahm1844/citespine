"""Global constants used across CiteSpine."""

from datetime import date

# Embeddings / Retrieval
EMBED_DIM: int = 384  # all-MiniLM-L6-v2
DEFAULT_TOP_K: int = 10

# Chunking
CHUNK_SIZE_TOKENS: int = 900
CHUNK_OVERLAP_TOKENS: int = 150

# Metadata required fields
REQUIRED_DOC_FIELDS = (
    "title",
    "doc_type",
    "framework",
    "jurisdiction",
    "authority_level",
    "effective_date",
    "version",
)

# Defaults
DEFAULT_AS_OF: str = "2023-12-31"

# Paths (relative to repo root)
DATA_DIR = "data"
RAW_DIR = f"{DATA_DIR}/raw"
PROCESSED_DIR = f"{DATA_DIR}/processed"
EVAL_DIR = f"{DATA_DIR}/eval"
MANIFESTS_DIR = f"{DATA_DIR}/manifests"
LOGS_DIR = "logs"

# Filenames
EXCEPTIONS_CSV = f"{PROCESSED_DIR}/exceptions.csv"
INDEX_MANIFEST_JSON = f"{PROCESSED_DIR}/index_manifest.json"
SEED_QUESTIONS_JSONL = "src/eval/seed_questions.jsonl"

# Governance rule
NO_CITATION_NO_CLAIM = True

# Display limits
MAX_CITATION_SNIPPET_CHARS = 280
