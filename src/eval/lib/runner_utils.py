import os, json, sys, time

def not_impl(report_path: str, runner_name: str):
    payload = {"status": "NOT_IMPLEMENTED", "runner": runner_name, "ts": int(time.time())}
    with open(report_path, "w", encoding="utf-8") as f: json.dump(payload, f)
    if os.getenv("ALLOW_NOT_IMPLEMENTED") == "1":
        sys.exit(0)
    sys.exit(1)
