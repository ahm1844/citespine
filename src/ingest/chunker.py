"""Section-aware chunker (initially naive; improved later with headings)."""
import re
from typing import List

def _approx_tokens(text: str) -> List[str]:
    return re.findall(r"\S+", text)

def chunk_text(text: str, target_tokens: int, overlap: int) -> List[str]:
    tokens = _approx_tokens(text)
    out, i = [], 0
    step = max(1, target_tokens - overlap)
    while i < len(tokens):
        seg = tokens[i:i+target_tokens]
        if not seg:
            break
        out.append(" ".join(seg))
        i += step
    return out

def count_tokens(text: str) -> int:
    return len(_approx_tokens(text))
