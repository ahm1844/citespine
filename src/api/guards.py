from time import time
from collections import defaultdict
from fastapi import HTTPException, Request

BUCKET = defaultdict(lambda: {"tokens": 0.0, "ts": time()})

def parse_rate(s: str):
    n, per = s.split("/")
    n = float(n)
    sec = {"second":1,"sec":1,"s":1,"minute":60,"min":60,"m":60,"hour":3600,"h":3600}[per]
    return n, sec

def demo_rate_limit(limit_str: str):
    max_tokens, period = parse_rate(limit_str)
    refill_per_sec = max_tokens / period
    async def _guard(request: Request):
        ip = request.client.host if request.client else "unknown"
        now = time()
        b = BUCKET[ip]
        b["tokens"] = min(max_tokens, b["tokens"] + (now - b["ts"]) * refill_per_sec)
        b["ts"] = now
        if b["tokens"] >= 1.0:
            b["tokens"] -= 1.0
            return
        raise HTTPException(status_code=429, detail="Demo rate limit exceeded")
    return _guard
