from __future__ import annotations
import argparse, hashlib, secrets
from ..db.session import get_session
from ..db.models import APIKey

def create(name: str) -> str:
    raw = secrets.token_urlsafe(32)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    s = get_session()
    s.add(APIKey(name=name, key_hash=digest, active=True))
    s.commit()
    return raw

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Create an API key")
    ap.add_argument("--name", required=True, help="Label for the key (e.g., client name)")
    args = ap.parse_args()
    print(create(args.name))
