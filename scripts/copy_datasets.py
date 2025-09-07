import os, shutil, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]  # repo root
src = ROOT / "src" / "eval" / "datasets" / "v1"
dst = ROOT / "src" / "eval" / "datasets"

files = ["time_travel.jsonl","negative_controls.jsonl","adversarial_prompts.jsonl","tables_ocr.jsonl","conflicts.jsonl"]
for f in files:
    s = src / f
    d = dst / f
    if d.exists() and d.is_symlink(): continue
    shutil.copyfile(s, d)
print("Datasets copied from v1/ (symlink fallback).")
