"""Compose grounded answers strictly from retrieved evidence (no hallucinations)."""
from typing import Dict, List
from ..common.constants import MAX_CITATION_SNIPPET_CHARS, NO_CITATION_NO_CLAIM
from opentelemetry import trace

tr = trace.get_tracer("citespine")

def _snippet(text: str) -> str:
    t = " ".join(text.split())
    return t[:MAX_CITATION_SNIPPET_CHARS] + ("…" if len(t) > MAX_CITATION_SNIPPET_CHARS else "")

def compose_answer(evidence: List[Dict]) -> Dict:
    with tr.start_as_current_span("compose.answer"):
        if not evidence:
            return {
                "answer": "No evidence found in the specified corpus and filters.",
                "citations": []
            }

        # Simple extractive approach: take top N passages as bullet points.
        bullets = []
        citations = []
        for ev in evidence[:5]:
            bullets.append(f"- { _snippet(ev['text']) }")
            citations.append({
                "chunk_id": ev["chunk_id"],
                "section_path": ev.get("section_path") or "",
                "page_span": [ev.get("page_start") or 0, ev.get("page_end") or 0]
            })

        answer = "Here are the most relevant cited passages:\n" + "\n".join(bullets)
        if NO_CITATION_NO_CLAIM and not citations:
            answer = "No evidence found in the specified corpus and filters."

        return {"answer": answer, "citations": citations}
