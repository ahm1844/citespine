"""Structured logging setup (console + file)."""
import sys
from pathlib import Path
from loguru import logger
from .constants import LOGS_DIR

_LOG_DIR = Path(LOGS_DIR)
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_LOG_FILE = _LOG_DIR / "app.log"

# Configure sinks (console & file)
logger.remove()
logger.add(sys.stdout, level="INFO", enqueue=True, backtrace=False, diagnose=False)
logger.add(_LOG_FILE, level="INFO", rotation="5 MB", retention="14 days", enqueue=True)

def get_logger(name: str):
    return logger.bind(component=name)
