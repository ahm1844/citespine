import os, sys, json, glob, math
from typing import Any, Dict
import yaml

REPORTS = {
    "faithfulness": "data/eval/faithfulness_report.json",
    "filters": "data/eval/filter_leak_report.json",
    "asof": "data/eval/asof_report.json",
    "negatives": "data/eval/negatives_report.json",
    "structured": "data/eval/structured_fidelity.json",
    "perf": "data/eval/perf_load.json",
    "replay": "data/eval/replay_report.json",
    "pii": "data/eval/pii_redaction_report.json"
}

def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def metric(report: Dict[str, Any], path: str, default=None):
    cur = report
    for p in path.split("."):
        if p not in cur: return default
        cur = cur[p]
    return cur

def check_threshold(name: str, value: float, rule: Dict[str, float]) -> bool:
    if "gte" in rule: return value is not None and value >= float(rule["gte"])
    if "lte" in rule: return value is not None and value <= float(rule["lte"])
    if "eq"  in rule: return value is not None and abs(value - float(rule["eq"])) < 1e-9
    return False

def main():
    cfg = yaml.safe_load(open("docs/ACCEPTANCE_GATES.yaml", "r", encoding="utf-8"))
    allow_not_impl = os.getenv("ALLOW_NOT_IMPLEMENTED") == "1"
    failures = []

    # Load all reports (if missing and not-impl allowed, mark soft-fail)
    reports = {}
    for key, path in REPORTS.items():
        try:
            reports[key] = load_json(path)
        except Exception:
            if allow_not_impl:
                reports[key] = {"status":"NOT_IMPLEMENTED"}
            else:
                failures.append(f"[{key}] missing report: {path}")

    # Short-circuit if any hard-missing and not allowed
    if failures and not allow_not_impl:
        print("\n".join(failures)); sys.exit(1)

    # If NOT_IMPLEMENTED and not allowed -> fail
    for k, rep in reports.items():
        if isinstance(rep, dict) and rep.get("status") == "NOT_IMPLEMENTED" and not allow_not_impl:
            failures.append(f"[{k}] runner NOT_IMPLEMENTED")

    # Extract metrics from reports (aligning to your schema)
    # Faithfulness
    if "faithfulness" in reports:
        r = reports["faithfulness"].get("summary", {})
        checks = {
            ("quality.faithfulness.unsupported_claim_rate", "unsupported"): r.get("unsupported", 0)/max(1, r.get("claims_total",1)),
            ("quality.faithfulness.citation_span_precision", "span_precision"): r.get("span_precision"),
            ("quality.faithfulness.citation_span_recall", "span_recall"): r.get("span_recall"),
        }
        for (rule_path, label), val in checks.items():
            rule = cfg
            for part in rule_path.split("."): rule = rule[part]
            if not check_threshold(label, val, rule): failures.append(f"[faithfulness] {label}={val} violates {rule}")

    # Retrieval rank (MRR@10, FCR median) – from faithfulness report or a rank report as you prefer
    if "faithfulness" in reports:
        r = reports["faithfulness"].get("summary", {})
        rr = cfg["quality"]["retrieval_rank"]
        if not check_threshold("mrr_at_10", r.get("mrr_at_10"), rr["mrr_at_10"]):
            failures.append(f"[rank] mrr_at_10={r.get('mrr_at_10')} violates {rr['mrr_at_10']}")
        if not check_threshold("first_correct_rank_median", r.get("first_correct_rank_median"), rr["first_correct_rank_median"]):
            failures.append(f"[rank] first_correct_rank_median={r.get('first_correct_rank_median')} violates {rr['first_correct_rank_median']}")

    # Filters
    if "filters" in reports:
        r = reports["filters"].get("summary", {})
        fl = cfg["filters"]
        if not check_threshold("retrieval_leak_rate", r.get("retrieval_leak_rate"), fl["retrieval_leak_rate"]):
            failures.append(f"[filters] retrieval_leak_rate={r.get('retrieval_leak_rate')} violates {fl['retrieval_leak_rate']}")
        if not check_threshold("answer_leak_rate", r.get("answer_leak_rate"), fl["answer_leak_rate"]):
            failures.append(f"[filters] answer_leak_rate={r.get('answer_leak_rate')} violates {fl['answer_leak_rate']}")

    # Temporal
    if "asof" in reports:
        r = reports["asof"].get("summary", {})
        tl = cfg["temporal_accuracy"]["version_leakage_rate"]
        if not check_threshold("version_leakage_rate", r.get("leak_rate"), tl):
            failures.append(f"[asof] leak_rate={r.get('leak_rate')} violates {tl}")

    # Negatives
    if "negatives" in reports:
        r = reports["negatives"].get("summary", {})
        ng = cfg["negatives"]["false_positive_rate"]
        if not check_threshold("false_positive_rate", r.get("false_positive_rate"), ng):
            failures.append(f"[negatives] false_positive_rate={r.get('false_positive_rate')} violates {ng}")

    # Structured
    if "structured" in reports:
        r = reports["structured"].get("summary", {})
        st = cfg["structured_outputs"]
        if not check_threshold("field_source_coverage", r.get("coverage"), st["field_source_coverage"]):
            failures.append(f"[structured] coverage={r.get('coverage')} violates {st['field_source_coverage']}")
        if not check_threshold("false_fills_rate", r.get("false_fills"), st["false_fills_rate"]):
            failures.append(f"[structured] false_fills={r.get('false_fills')} violates {st['false_fills_rate']}")

    # Perf
    if "perf" in reports:
        r = reports["perf"].get("summary", {})
        pf = cfg["performance"]
        if not check_threshold("p50_ms", r.get("p50_ms"), pf["p50_ms"]): failures.append(f"[perf] p50={r.get('p50_ms')} violates {pf['p50_ms']}")
        if not check_threshold("p95_ms", r.get("p95_ms"), pf["p95_ms"]): failures.append(f"[perf] p95={r.get('p95_ms')} violates {pf['p95_ms']}")
        if not check_threshold("error_rate", r.get("error_rate", 0.0), pf["error_rate"]): failures.append(f"[perf] error_rate={r.get('error_rate')} violates {pf['error_rate']}")

    # Repro
    if "replay" in reports:
        r = reports["replay"].get("summary", {})
        rp = cfg["reproducibility"]
        if not check_threshold("retrieval_identity", r.get("retrieval_identity"), rp["retrieval_identity"]):
            failures.append(f"[replay] retrieval_identity={r.get('retrieval_identity')} violates {rp['retrieval_identity']}")
        if not check_threshold("answer_similarity", r.get("answer_similarity"), rp["answer_similarity"]):
            failures.append(f"[replay] answer_similarity={r.get('answer_similarity')} violates {rp['answer_similarity']}")

    # Security & PII
    if "pii" in reports:
        r = reports["pii"].get("summary", {})
        pi = cfg["pii"]
        if not check_threshold("redaction_recall", r.get("recall"), pi["redaction_recall"]):
            failures.append(f"[pii] recall={r.get('recall')} violates {pi['redaction_recall']}")
        if not check_threshold("redaction_precision", r.get("precision"), pi["redaction_precision"]):
            failures.append(f"[pii] precision={r.get('precision')} violates {pi['redaction_precision']}")

    if failures:
        print("\n".join(failures))
        sys.exit(1)
    print("All gates satisfied (or allowed via ALLOW_NOT_IMPLEMENTED).")
    sys.exit(0)

if __name__ == "__main__":
    main()