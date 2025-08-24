"""SQLAlchemy engine/session and pgvector extension bootstrap."""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from ..common.config import SETTINGS
from ..common.logging import get_logger

log = get_logger("db/session")

_engine = create_engine(SETTINGS.PG_DSN, future=True)
SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, future=True)

def init_extensions():
    with _engine.connect() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            log.info("pgvector extension ensured.")
        except Exception as e:
            log.error(f"Error ensuring pgvector extension: {e}")
            raise

def get_engine():
    return _engine

def get_session():
    return SessionLocal()
