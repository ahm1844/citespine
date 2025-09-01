from __future__ import annotations
import re
from ..common.config import SETTINGS
from ..common.logging import get_logger

log = get_logger("retrieval/synonyms")

# Minimal, high-signal expansions for PCAOB/ESEF
# Keep tight to avoid spurious matches.
_PATTERNS: list[tuple[re.Pattern, str | callable]] = [
    # ICFR
    (re.compile(r"\bICFR\b", re.I),
     '("internal control over financial reporting" OR ICFR)'),
    # ESEF
    (re.compile(r"\bESEF\b", re.I),
     '("European Single Electronic Format" OR ESEF)'),
    # iXBRL / XBRL
    (re.compile(r"\biXBRL\b", re.I),
     '("inline XBRL" OR iXBRL)'),
    (re.compile(r"\bXBRL\b", re.I),
     '("eXtensible Business Reporting Language" OR XBRL)'),
    # PCAOB Auditing Standard numbers (AS 2201, etc.)
    (re.compile(r"\bAS\s?(\d{3,4})\b", re.I),
     lambda m: f'("Auditing Standard {m.group(1)}" OR "AS {m.group(1)}")'),
]

def expand_for_sparse(q: str) -> str:
    original = q
    s = q
    for pat, rep in _PATTERNS:
        s = pat.sub(rep if isinstance(rep, str) else rep, s)
    if SETTINGS.SYN_DEBUG_LOG and s != original:
        log.info(f"SYN EXPAND: '{original}' -> '{s}'")
    # Guard: keep query length bounded to avoid pathological expansions
    if len(s) > 512:
        s = s[:512]
    return s
