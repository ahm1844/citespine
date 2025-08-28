"""Progress logger: append-only, atomic writes."""
from pathlib import Path
from datetime import datetime
from .constants import LOGS_DIR

def log_progress(task: str, status: str, details: str = ""):
    path = Path(LOGS_DIR) / "progress.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:  # append only
        f.write(f"{datetime.utcnow().isoformat()}\t{task}\t{status}\t{details}\n")