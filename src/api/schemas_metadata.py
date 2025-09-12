from __future__ import annotations
from typing import Optional, Literal, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

Framework = Literal["IFRS","US_GAAP","Other"]
Jurisdiction = Literal["US","EU","UK","Global","Other"]
DocType = Literal["standard","release","order","manual","guidelines","policy","filing","memo","qna","staff_alert"]
AuthorityLevel = Literal["authoritative","interpretive","internal_policy"]

class EvidenceSpan(BaseModel):
    page: int
    start: int
    end: int
    text: str
    locator: str  # e.g., "title_block", "running_header", "body", "pdf_meta"

class FieldCandidate(BaseModel):
    value: str
    score: float = 0.0
    evidence: List[EvidenceSpan] = []

class MetadataField(BaseModel):
    value: Optional[str]
    confidence: float = 0.0
    evidence: List[EvidenceSpan] = []
    method: str = "fusion"  # "fusion" | "heuristic" | "llm" | "user"

class MetadataExtraction(BaseModel):
    source_id: str
    framework: MetadataField
    jurisdiction: MetadataField
    doc_type: MetadataField
    authority_level: MetadataField
    effective_date: MetadataField  # ISO 8601 yyyy-mm-dd or None
    version: MetadataField
    conflict_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
