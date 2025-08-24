"""Progress logger for engineering steps (simple, human-readable)."""
from pathlib import Path
from datetime import datetime
from .constants import LOGS_DIR

_PROGRESS_FILE = Path(LOGS_DIR) / "progress.log"
_PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)

def log_progress(task: str, status: str, details: str = ""):
    ts = datetime.utcnow().isoformat()
    line = f"{ts}\t{task}\t{status}\t{details}\n"
    _PROGRESS_FILE.write_text(_PROGRESS_FILE.read_text() + line if _PROGRESS_FILE.exists() else line)
