import os

def assert_offline_forbids_http():
    if os.getenv("OFFLINE", "false").lower() in ("1","true","yes"):
        raise RuntimeError("OFFLINE=true: external HTTP/LLM providers are disabled.")

def ensure_online_allowed():
    if os.getenv("OFFLINE", "false").lower() in ("1","true","yes"):
        raise RuntimeError("OFFLINE=true: online providers not permitted.")
