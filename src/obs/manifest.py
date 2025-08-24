"""Run manifest writer to ensure reproducibility (answers, eval, index)."""
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from ..common.constants import MANIFESTS_DIR

def _ensure_dir() -> Path:
    d = Path(MANIFESTS_DIR)
    d.mkdir(parents=True, exist_ok=True)
    return d

def corpus_hash(processed_dir: str) -> str:
    """Hash all JSONL under processed_dir (order-insensitive by combining file hashes)."""
    p = Path(processed_dir)
    digests = []
    for f in sorted(p.glob("*.jsonl")):
        digests.append(hashlib.sha256(f.read_bytes()).hexdigest())
    final = hashlib.sha256("".join(digests).encode("utf-8")).hexdigest()
    return final

def write_manifest(kind: str, payload: Dict[str, Any]) -> str:
    """Write manifest JSON under data/manifests and return its path."""
    d = _ensure_dir()
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    path = d / f"{kind}_{ts}.json"
    payload = {**payload, "kind": kind, "created_at": datetime.utcnow().isoformat()}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)
