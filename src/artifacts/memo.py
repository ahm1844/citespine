from typing import Dict, List
from ..answer.compose import _snippet  # reuse snippet for short field text

def build_memo(evidence: List[Dict]) -> Dict:
    out = {
        "title": "",
        "issue": "",
        "analysis": "",
        "conclusion": "",
        "references": [],
        "_source_map": [],
        "_flags": {}
    }
    if not evidence:
        out["_flags"]["issue"] = "missing_evidence"
        out["_flags"]["analysis"] = "missing_evidence"
        out["_flags"]["conclusion"] = "missing_evidence"
        return out

    out["references"] = [e["chunk_id"] for e in evidence]
    out["_source_map"] = [
        {"field": "analysis", "chunk_id": e["chunk_id"], "page_span": [e.get("page_start") or 0, e.get("page_end") or 0]}
        for e in evidence[:3]
    ]
    # Minimal safe fill
    out["issue"] = _snippet(evidence[0]["text"])
    out["analysis"] = "\n".join(_snippet(e["text"]) for e in evidence[:3])
    out["conclusion"] = ""  # leave blank unless explicit conclusion spans are found
    if not out["conclusion"]:
        out["_flags"]["conclusion"] = "missing_evidence"
    return out
