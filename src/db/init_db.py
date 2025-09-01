"""Create tables and indexes."""
from sqlalchemy import text
from sqlalchemy.engine import Connection
from .session import get_engine, init_extensions, get_session
from .models import Base
from .dao import create_ivfflat_index_if_missing
from ..common.logging import get_logger

log = get_logger("db/init")

def _ensure_fts(session):
    """
    Optional: create a concurrent GIN expression index on to_tsvector(text).
    - No table rewrite
    - Safe to skip entirely for small corpora (planner will seq-scan)
    - Must run in AUTOCOMMIT for CONCURRENTLY
    """
    try:
        engine = session.get_bind()
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:  # type: Connection
            # Expression index matches the sparse query EXACTLY (coalesce+english)
            conn.execute(text("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chunks_fts_expr
                ON chunks
                USING GIN (to_tsvector('english', coalesce(text, '')))
            """))
    except Exception as e:
        # Non-fatal in PoC; we can run without an index
        log.warning(f"FTS index creation skipped: {e}")

def init_db():
    init_extensions()
    engine = get_engine()
    Base.metadata.create_all(engine)
    session = get_session()
    create_ivfflat_index_if_missing(session)
    _ensure_fts(session)
    log.info("Database initialized with tables, ANN index, and FTS index.")

if __name__ == "__main__":
    init_db()
