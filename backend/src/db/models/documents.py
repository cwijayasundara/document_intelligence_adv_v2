"""Document-related ORM models: categories, documents, summaries."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models.base import Base, TimestampMixin


class DocumentCategory(TimestampMixin, Base):
    """User-defined document classification categories."""

    __tablename__ = "document_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    classification_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    documents: Mapped[list[Document]] = relationship(back_populates="category")
    extraction_schemas: Mapped[list["ExtractionSchema"]] = relationship(
        back_populates="category"
    )


class Document(TimestampMixin, Base):
    """Core document metadata and state machine status."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    original_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    parsed_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'uploaded'"), index=True
    )
    document_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_categories.id"),
        nullable=True,
        index=True,
    )
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    parse_confidence_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    category: Mapped[DocumentCategory | None] = relationship(back_populates="documents")
    extracted_values: Mapped[list["ExtractedValue"]] = relationship(
        back_populates="document"
    )
    summary: Mapped[DocumentSummary | None] = relationship(back_populates="document")
    bulk_job_documents: Mapped[list["BulkJobDocument"]] = relationship(
        back_populates="document"
    )


class DocumentSummary(Base):
    """Generated document summaries with cache invalidation."""

    __tablename__ = "document_summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    key_topics: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'")
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    document: Mapped[Document] = relationship(back_populates="summary")
