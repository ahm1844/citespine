"""ORM models for Document and Chunk (with pgvector)."""
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from sqlalchemy import String, Text, Date, Integer, ForeignKey, ForeignKeyConstraint, Index, UniqueConstraint, Boolean, DateTime, Float, Computed
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from datetime import datetime, timezone
from ..common.constants import EMBED_DIM

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"

    source_id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    doc_type: Mapped[str] = mapped_column(String, nullable=False)
    framework: Mapped[str] = mapped_column(String, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String, nullable=False)
    authority_level: Mapped[str] = mapped_column(String, nullable=False)
    effective_date: Mapped[str] = mapped_column(Date, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    ingest_ts: Mapped[str] = mapped_column(String, nullable=True)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    hash: Mapped[str] = mapped_column(String, nullable=False)

    chunks: Mapped[list["Chunk"]] = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_doc_filters", "framework", "jurisdiction", "doc_type", "authority_level"),
        Index("idx_doc_asof", "framework", "jurisdiction", "effective_date", "version"),
    )

class Chunk(Base):
    __tablename__ = "chunks"

    chunk_id: Mapped[str] = mapped_column(String, primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("documents.source_id", ondelete="CASCADE"), nullable=False)
    section_path: Mapped[str] = mapped_column(Text, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    tokens: Mapped[int] = mapped_column(Integer, nullable=True)
    page_start: Mapped[int] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int] = mapped_column(Integer, nullable=True)

    # denormalized for fast filters
    framework: Mapped[str] = mapped_column(String, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String, nullable=False)
    doc_type: Mapped[str] = mapped_column(String, nullable=False)
    authority_level: Mapped[str] = mapped_column(String, nullable=False)
    effective_date: Mapped[str] = mapped_column(Date, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)

    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBED_DIM), nullable=True)

    # Enhanced citation fields
    para_no: Mapped[int] = mapped_column(Integer, nullable=True)
    section_id: Mapped[str] = mapped_column(String, nullable=True)
    char_start: Mapped[int] = mapped_column(Integer, nullable=True)
    char_end: Mapped[int] = mapped_column(Integer, nullable=True)
    span_hash: Mapped[str] = mapped_column(String, nullable=True)

    # Generated MD5 hash column for efficient unique constraint
    text_md5: Mapped[str] = mapped_column(
        String(32),
        Computed("md5(text)", persisted=True),
        nullable=False
    )

    document: Mapped[Document] = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("idx_chunk_filters", "framework", "jurisdiction", "doc_type", "authority_level"),
        Index("idx_chunk_asof", "framework", "jurisdiction", "effective_date", "version"),
        UniqueConstraint("source_id", "section_path", "text_md5", name="uq_chunks_src_section_textmd5"),
        ForeignKeyConstraint(
            ["section_id"], ["document_sections.section_id"], ondelete="SET NULL", use_alter=True
        ),
    )

class APIKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
    key_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)  # sha256
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

def _utcnow():
    return datetime.now(timezone.utc)

class DocumentSection(Base):
    __tablename__ = "document_sections"
    section_id: Mapped[str] = mapped_column(String, primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("documents.source_id", ondelete="CASCADE"), nullable=False)
    parent_id: Mapped[str] = mapped_column(ForeignKey("document_sections.section_id", ondelete="CASCADE"), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    number: Mapped[str] = mapped_column(String, nullable=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("idx_sections_source", "source_id"),
    )

class DocumentAnalysis(Base):
    __tablename__ = "document_analysis"
    source_id: Mapped[str] = mapped_column(String, primary_key=True)
    mode: Mapped[str] = mapped_column(String, nullable=False, default="fast")
    mode_used: Mapped[str] = mapped_column(String, nullable=True)
    lang: Mapped[str] = mapped_column(String, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    topics: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    questions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    overview: Mapped[dict] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, default=_utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
