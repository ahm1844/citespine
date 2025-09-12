from __future__ import annotations
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

AnalysisMode = Literal["fast", "smart", "deep", "fast(fallback)", "smart(fallback)", "deep(fallback)"]

class EvidenceHighlight(BaseModel):
    start: int
    end: int

class EvidenceSegment(BaseModel):
    chunk_id: str
    page: Optional[int] = None
    section: Optional[str] = None
    text: str
    highlights: List[EvidenceHighlight] = Field(default_factory=list)
    relevance: float = 0.0
    type: Optional[str] = None
    model_config = ConfigDict(extra="forbid")

class QueryReq(BaseModel):
    q: str
    filters: Optional[Dict[str, Any]] = None
    top_k: int = 10
    probes: int = 15
    focus_source_id: Optional[str] = None
    expected_evidence_type: Optional[str] = None
    boost_terms: Optional[List[str]] = None
    model_config = ConfigDict(extra="ignore")

class QueryResp(BaseModel):
    answer: str
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_segments: List[EvidenceSegment] = Field(default_factory=list)
    metrics: Dict[str, Any]

# ------- Analysis / Overview -------
class OverviewCitation(BaseModel):
    id: str
    chunk_id: str
    page: int
    section_path: str
    evidence_type: Optional[str] = None
    score: float = 0.0
    highlights: List[EvidenceHighlight] = Field(default_factory=list)
    text: Optional[str] = None
    model_config = ConfigDict(extra="forbid")

class OverviewSection(BaseModel):
    text: str = ""
    citation_ids: List[str] = Field(default_factory=list)

class Overview(BaseModel):
    overview_markdown: str
    purpose: OverviewSection
    scope: OverviewSection
    key_requirements: List[OverviewSection] = Field(default_factory=list)
    effective_dates: List[OverviewSection] = Field(default_factory=list)
    amendments: List[OverviewSection] = Field(default_factory=list)
    affected_parties: OverviewSection
    citations: List[OverviewCitation] = Field(default_factory=list)
    model_config = ConfigDict(extra="forbid")

class AnalysisResult(BaseModel):
    source_id: str
    mode: str
    lang: str
    summary: str
    topics: List[str] = Field(default_factory=list)
    questions: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.0
    ready: bool = True
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    # NEW to end schema drift:
    overview: Optional[Overview] = None
    mode_used: Optional[AnalysisMode] = None
    model_config = ConfigDict(extra="ignore")

# Legacy schemas for backwards compatibility
class Suggestion(BaseModel):
    text: str
    source_id: str
    confidence: float = 0.0

class UploadResponse(BaseModel):
    accepted: bool = True
    source_id: str  
    message: str = "Upload successful"
    analysis_ready: bool = False