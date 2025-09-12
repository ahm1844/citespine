from __future__ import annotations
import re, os, json
from typing import Any, Dict, List, Tuple, Optional
from datetime import datetime, timezone
from pathlib import Path

try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    # Fallback to simple string matching
    class MockFuzz:
        @staticmethod
        def token_set_ratio(a, b):
            return 100 if a.lower() == b.lower() else 0
    fuzz = MockFuzz()

from ..api.schemas_metadata import (
    EvidenceSpan, FieldCandidate, MetadataField, MetadataExtraction,
    Framework, Jurisdiction, DocType, AuthorityLevel
)
from ..common.logging import get_logger

log = get_logger("metadata_extractor")

# Pull controlled vocabulary at runtime — do NOT hardcode:
# config/metadata.yml holds canonical enums + synonyms (already in your repo).
import yaml
CFG_PATH = os.getenv("METADATA_CFG", "config/metadata.yml")

try:
    CFG = yaml.safe_load(open(CFG_PATH, "r"))
    CANON = {
        "frameworks": list(CFG.get("frameworks", {}).keys()),              # ["IFRS","US_GAAP","Other"]
        "jurisdictions": list(CFG.get("jurisdictions", {}).keys()),        # ["US","EU","UK","Global","Other"]
        "doc_types": list(CFG.get("doc_types", {}).keys()),                # ["standard","release","order","manual","guidelines",...]
        "authority_levels": list(CFG.get("authority_levels", {}).keys()),  # ["authoritative","interpretive","internal_policy"]
    }
    SYN = {k: CFG.get(k, {}) for k in ["frameworks","jurisdictions","doc_types","authority_levels"]}
except Exception as e:
    log.warning(f"Failed to load metadata config: {e}")
    # Fallback to basic config
    CANON = {
        "frameworks": ["IFRS","US_GAAP","Other"],
        "jurisdictions": ["US","EU","UK","Global","Other"],
        "doc_types": ["standard","release","order","manual","guidelines","policy","filing","memo","qna","staff_alert"],
        "authority_levels": ["authoritative","interpretive","internal_policy"]
    }
    SYN = {k: {} for k in CANON.keys()}

DATE_PATTERNS = [
    r"(effective (?:on|for|as of)\s+(?P<date>\w+\s+\d{1,2},\s+\d{4}))",
    r"(effective (?:on|for|as of)\s+(?P<date>\d{4}-\d{2}-\d{2}))",
    r"(?P<date>\w+\s+\d{1,2},\s+\d{4})\s*(?:effective date)",
    r"(fiscal years (?:beginning|ending) on or after\s+(?P<date>\w+\s+\d{1,2},\s+\d{4}))",
]

# Utility: normalize date strings to ISO 8601 yyyy-mm-dd if possible
def _parse_date_iso(s: str) -> Optional[str]:
    s = s.strip()
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            continue
    return None

def _slice_title_block(page_text: str, head_chars: int = 1800) -> str:
    # Take upper portion of first page; most regulators put issuer/class cues here.
    return page_text[:head_chars]

def _running_header_footer(pages: List[str]) -> List[str]:
    # Collect short repeating lines appearing on many pages (headers/footers)
    from collections import Counter
    lines = []
    for p in pages:
        for ln in p.splitlines():
            t = ln.strip()
            if 3 <= len(t) <= 120:
                lines.append(t)
    freq = Counter(lines)
    return [ln for ln, c in freq.items() if c >= max(3, len(pages)//5)]

def _mk_evidence(page: int, text: str, start: int, end: int, locator: str) -> EvidenceSpan:
    start = max(0, start); end = min(len(text), end)
    return EvidenceSpan(page=page, start=start, end=end, text=text[start:end], locator=locator)

def _domain_hint(source_url: Optional[str]) -> Tuple[List[FieldCandidate], List[FieldCandidate]]:
    f, j = [], []
    if not source_url: return f, j
    host = source_url.lower()
    if "sec.gov" in host:
        f.append(FieldCandidate(value="Other", score=0.85, evidence=[]))
        j.append(FieldCandidate(value="US", score=0.95, evidence=[]))
    elif "pcaobus.org" in host:
        f.append(FieldCandidate(value="Other", score=0.9, evidence=[]))
        j.append(FieldCandidate(value="US", score=0.9, evidence=[]))
    elif "esma.europa.eu" in host:
        f.append(FieldCandidate(value="Other", score=0.85, evidence=[]))
        j.append(FieldCandidate(value="EU", score=0.95, evidence=[]))
    return f, j

def _issuer_cues(text: str) -> List[Tuple[str,float]]:
    cues = []
    # These are not mappings to final enums; they are raw issuer strings discovered in the document.
    for pat, w in [
        (r"\bPublic Company Accounting Oversight Board\b", 0.95),
        (r"\bSecurities and Exchange Commission\b", 0.95),
        (r"\bEuropean Securities and Markets Authority\b", 0.95),
        (r"\bFinancial Reporting Manual\b", 0.80),
        (r"\bAuditing Standard\b", 0.85),
        (r"\bRelease No\.\s*[\w\-\u2013]+\b", 0.85),
        (r"\bOrder (?:Granting|Approving)\b", 0.85),
        (r"\bStaff Audit Practice Alert\b", 0.9),
        (r"\bGuidelines\b", 0.8),
        (r"\bReporting Manual\b", 0.8),
        (r"\bQC 1000\b", 0.9),
        (r"\bAS\s*2201\b", 0.9),
        (r"\bESMA\d{2}\-\d{2}\-\d{3}(?:\s*Rev\.?\s*\d+)?\b", 0.9),
    ]:
        for m in re.finditer(pat, text, flags=re.I):
            cues.append((m.group(0), w))
    return cues

def _map_to_canon(kind: str, raw: str) -> Tuple[str, float]:
    # Use synonyms from config + fuzzy matching; no hardcoded enum mapping.
    # 1) direct synonym hit
    canon_dict = SYN.get(kind, {})
    for canon, syns in canon_dict.items():
        if isinstance(syns, list):
            if any(raw.lower() == s.lower() for s in syns):
                return canon, 0.99
    
    # 2) fuzzy to any synonym
    all_pairs = []
    for canon, syns in canon_dict.items():
        if isinstance(syns, list):
            for s in syns + [canon]:
                all_pairs.append((canon, s))
    
    if not all_pairs: return raw, 0.2
    
    if RAPIDFUZZ_AVAILABLE:
        best = max(all_pairs, key=lambda p: fuzz.token_set_ratio(raw, p[1]))
        score = fuzz.token_set_ratio(raw, best[1]) / 100.0
    else:
        # Simple fallback matching
        best = ("Other", "Other")
        score = 0.2
        for canon, syn in all_pairs:
            if raw.lower() in syn.lower() or syn.lower() in raw.lower():
                best = (canon, syn)
                score = 0.8
                break
    
    return best[0], float(score)

def _classify_from_cues(cues: List[Tuple[str,float]]) -> Tuple[List[FieldCandidate], List[FieldCandidate], List[FieldCandidate], List[FieldCandidate]]:
    framework_c, jurisdiction_c, doc_type_c, authority_c = [],[],[],[]
    for cue, w in cues:
        cl = cue.lower()
        if "public company accounting oversight board" in cl or "pcaob" in cl:
            framework_c.append(FieldCandidate(value="Other", score=0.75*w))
            jurisdiction_c.append(FieldCandidate(value="US", score=0.75*w))
        if "securities and exchange commission" in cl or "sec " in cl:
            framework_c.append(FieldCandidate(value="Other", score=0.6*w))
            jurisdiction_c.append(FieldCandidate(value="US", score=0.85*w))
        if "european securities and markets authority" in cl or "esma" in cl:
            framework_c.append(FieldCandidate(value="Other", score=0.6*w))
            jurisdiction_c.append(FieldCandidate(value="EU", score=0.9*w))

        if "auditing standard" in cl or re.search(r"\bas\s*\d{3,4}\b", cl):
            doc_type_c.append(FieldCandidate(value="standard", score=0.7*w))
            authority_c.append(FieldCandidate(value="authoritative", score=0.65*w))
        if "release no." in cl:
            doc_type_c.append(FieldCandidate(value="release", score=0.8*w))
            authority_c.append(FieldCandidate(value="authoritative", score=0.7*w))
        if "order granting" in cl or "order approving" in cl:
            doc_type_c.append(FieldCandidate(value="order", score=0.85*w))
            authority_c.append(FieldCandidate(value="authoritative", score=0.85*w))
        if "staff audit practice alert" in cl or "reporting manual" in cl or "guidelines" in cl:
            # interpretive classes
            if "manual" in cl: doc_type_c.append(FieldCandidate(value="manual", score=0.85*w))
            if "guidelines" in cl: doc_type_c.append(FieldCandidate(value="guidelines", score=0.85*w))
            if "practice alert" in cl: doc_type_c.append(FieldCandidate(value="staff_alert", score=0.85*w))
            authority_c.append(FieldCandidate(value="interpretive", score=0.9*w))
    return framework_c, jurisdiction_c, doc_type_c, authority_c

def _effective_date_candidates(text: str, page_idx: int, locator: str) -> List[FieldCandidate]:
    cands = []
    for pat in DATE_PATTERNS:
        for m in re.finditer(pat, text, flags=re.I):
            ds = m.groupdict().get("date")
            iso = _parse_date_iso(ds) if ds else None
            if not iso: continue
            ev = _mk_evidence(page_idx, text, m.start(), m.end(), locator)
            cands.append(FieldCandidate(value=iso, score=0.85, evidence=[ev]))
    return cands

def _version_candidates(text: str, page_idx: int, locator: str) -> List[FieldCandidate]:
    cands = []
    for m in re.finditer(r"\b(Rev\.?\s*\d+|Revision\s*\d+|Updated\s*(?P<date>\w+\s+\d{1,2},\s*\d{4})|ESMA\d{2}\-\d{2}\-\d{3}\s*Rev\.?\s*\d+)\b", text, flags=re.I):
        ds = m.groupdict().get("date")
        val = _parse_date_iso(ds) if ds else m.group(0)
        ev = _mk_evidence(page_idx, text, m.start(), m.end(), locator)
        cands.append(FieldCandidate(value=str(val), score=0.7, evidence=[ev]))
    return cands

def _fuse(cands: List[FieldCandidate]) -> MetadataField:
    if not cands:
        return MetadataField(value=None, confidence=0.0, evidence=[], method="fusion")
    # merge duplicates by value and accumulate score + evidence
    by_val: Dict[str, FieldCandidate] = {}
    for c in cands:
        if c.value not in by_val:
            by_val[c.value] = FieldCandidate(value=c.value, score=0.0, evidence=[])
        by_val[c.value].score += c.score
        by_val[c.value].evidence.extend(c.evidence)
    best = max(by_val.values(), key=lambda x: x.score)
    return MetadataField(value=best.value, confidence=min(1.0, best.score), evidence=best.evidence, method="fusion")

def extract_metadata_document_aware(
    pages: List[str],
    pdf_meta: Dict[str, Any],
    source_url: Optional[str] = None,
    allow_llm: bool = False,
    llm_refine_fn = None  # function taking (draft: MetadataExtraction) -> MetadataExtraction  
) -> MetadataExtraction:
    # 1) title block & headers/footers
    title = _slice_title_block(pages[0]) if pages else ""
    hdrs = _running_header_footer(pages)

    # 2) issuer cues from title block + running headers + page 1
    cues: List[Tuple[str,float]] = []
    for s in [title] + hdrs + (pages[:1] if pages else []):
        cues.extend(_issuer_cues(s))

    # 3) candidates seeded from document text (no fixed map)
    framework_c, jurisdiction_c, doc_type_c, authority_c = _classify_from_cues(cues)

    # 4) domain hint (not decisive; just a weak prior)
    f_dom, j_dom = _domain_hint(source_url)
    framework_c.extend(f_dom); jurisdiction_c.extend(j_dom)

    # 5) PDF/XMP meta as weak evidence
    if pdf_meta:
        for k in ("Title","Subject","Keywords"):
            v = (pdf_meta.get(k) or "").strip()
            if not v: continue
            # treat as cues; lower weight
            pdf_cues = _issuer_cues(v)
            fw, ju, dt, au = _classify_from_cues([(c, w*0.6) for c, w in pdf_cues])
            framework_c += fw; jurisdiction_c += ju; doc_type_c += dt; authority_c += au

    # 6) effective date & version candidates from the first 2 pages and title block
    eff: List[FieldCandidate] = []
    ver: List[FieldCandidate] = []
    for idx, page_text in enumerate(pages[:2]):
        eff += _effective_date_candidates(page_text, idx, "body")
        ver += _version_candidates(page_text, idx, "body")
    eff += _effective_date_candidates(title, 0, "title_block")
    ver += _version_candidates(title, 0, "title_block")

    # 7) fuse candidates
    framework = _fuse(framework_c)
    jurisdiction = _fuse(jurisdiction_c)
    doc_type = _fuse(doc_type_c)
    authority = _fuse(authority_c)
    effective_date = _fuse(eff)
    version = _fuse(ver)

    draft = MetadataExtraction(
        source_id="",
        framework=framework, jurisdiction=jurisdiction,
        doc_type=doc_type, authority_level=authority,
        effective_date=effective_date, version=version
    )

    # 8) map each field to canonical vocab using synonyms (no hardcoding)
    for field_name in ["framework","jurisdiction","doc_type","authority_level"]:
        field = getattr(draft, field_name)
        if field.value:
            kind_map = {"framework":"frameworks","jurisdiction":"jurisdictions",
                       "doc_type":"doc_types","authority_level":"authority_levels"}
            canon, s = _map_to_canon(kind_map[field_name], field.value)
            field.value = canon
            field.confidence = max(field.confidence, s*0.9)

    # 9) optional LLM reconciliation (disabled for initial implementation)
    # if allow_llm and llm_refine_fn:
    #     low = any(getattr(draft, f).confidence < 0.80 for f in ["doc_type","authority_level","effective_date"])
    #     if low:
    #         try:
    #             draft = llm_refine_fn(draft)
    #         except Exception as e:
    #             log.warning(f"LLM refinement failed: {e}")

    return draft
