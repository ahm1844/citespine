import json, subprocess, datetime, os, yaml, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
def read(p): return json.load(open(p, "r", encoding="utf-8"))
def get_commit():
    try: return subprocess.check_output(["git","rev-parse","--short","HEAD"], cwd=ROOT).decode().strip()
    except: return "unknown"
R = ROOT / "data" / "eval"
reports = {
  "faithfulness": R / "faithfulness_report.json",
  "filters": R / "filter_leak_report.json",
  "asof": R / "asof_report.json",
  "negatives": R / "negatives_report.json",
  "structured": R / "structured_fidelity.json",
  "perf": R / "perf_load.json",
  "replay": R / "replay_report.json",
  "pii": R / "pii_redaction_report.json"
}
cfg = yaml.safe_load(open(ROOT/"docs/ACCEPTANCE_GATES.yaml","r",encoding="utf-8"))
vals = {}
for k,p in reports.items():
    if p.exists():
        try: vals[k]=read(p)
        except: vals[k]={"error":"unreadable"}
    else:
        vals[k]={"status":"missing"}

now = datetime.datetime.utcnow().isoformat()+"Z"
commit = get_commit()
html = f"""<!doctype html><html><head><meta charset="utf-8"><title>CiteSpine Trust</title>
<style>body{{font-family:system-ui;margin:2rem}} code{{background:#f5f5f5;padding:.1rem .3rem}}</style></head><body>
<h1>Trust & Proof — Live Metrics</h1>
<p><b>Last updated:</b> {now} • <b>Commit:</b> <code>{commit}</code></p>
<h2>Acceptance Gates</h2>
<pre>{yaml.safe_dump(cfg, sort_keys=False)}</pre>
<h2>Reports</h2>
<ul>""" + "".join(
  f'<li><a href="/data/eval/{p.name}">{k}: {p.name}</a></li>' for k,p in reports.items()
) + """</ul>
</body></html>"""
OUT = ROOT / "public" / "trust.html"
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(html, encoding="utf-8")
print(f"Wrote {OUT}")
