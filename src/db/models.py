"""ORM models for Document and Chunk (with pgvector)."""
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from sqlalchemy import String, Text, Date, Integer, ForeignKey, Index, UniqueConstraint
from pgvector.sqlalchemy import Vector
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

    document: Mapped[Document] = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("idx_chunk_filters", "framework", "jurisdiction", "doc_type", "authority_level"),
        Index("idx_chunk_asof", "framework", "jurisdiction", "effective_date", "version"),
        UniqueConstraint("source_id", "section_path", "text", name="uq_source_section_text"),
    )
