"""Create tables and indexes."""
from .session import get_engine, init_extensions, get_session
from .models import Base
from .dao import create_ivfflat_index_if_missing
from ..common.logging import get_logger

log = get_logger("db/init")

def init_db():
    init_extensions()
    engine = get_engine()
    Base.metadata.create_all(engine)
    session = get_session()
    create_ivfflat_index_if_missing(session)
    log.info("Database initialized with tables and ANN index.")

if __name__ == "__main__":
    init_db()
