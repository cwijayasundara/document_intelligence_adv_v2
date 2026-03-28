"""SQLAlchemy 2.0 ORM models for all 10 database tables."""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


class TimestampMixin:
    """Mixin adding created_at and updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        onupdate=datetime.now,
    )


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
    documents: Mapped[list["Document"]] = relationship(back_populates="category")
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

    # Relationships
    category: Mapped[DocumentCategory | None] = relationship(back_populates="documents")
    extracted_values: Mapped[list["ExtractedValue"]] = relationship(back_populates="document")
    summary: Mapped["DocumentSummary | None"] = relationship(back_populates="document")
    bulk_job_documents: Mapped[list["BulkJobDocument"]] = relationship(back_populates="document")


class ExtractionSchema(Base):
    """Versioned extraction field definitions per category."""

    __tablename__ = "extraction_schemas"
    __table_args__ = (
        UniqueConstraint("category_id", "version", name="uq_extraction_schemas_category_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_categories.id"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    schema_yaml: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    category: Mapped[DocumentCategory] = relationship(back_populates="extraction_schemas")
    fields: Mapped[list["ExtractionField"]] = relationship(back_populates="schema")


class ExtractionField(Base):
    """Individual field definitions within an extraction schema."""

    __tablename__ = "extraction_fields"
    __table_args__ = (
        UniqueConstraint("schema_id", "field_name", name="uq_extraction_fields_schema_field"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    schema_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extraction_schemas.id"),
        nullable=False,
        index=True,
    )
    field_name: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    examples: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'string'")
    )
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    # Relationships
    schema: Mapped[ExtractionSchema] = relationship(back_populates="fields")
    extracted_values: Mapped[list["ExtractedValue"]] = relationship(back_populates="field")


class ExtractedValue(Base):
    """Extracted data per document per field, with confidence scoring."""

    __tablename__ = "extracted_values"
    __table_args__ = (
        UniqueConstraint("document_id", "field_id", name="uq_extracted_values_doc_field"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id"),
        nullable=False,
        index=True,
    )
    field_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extraction_fields.id"),
        nullable=False,
        index=True,
    )
    extracted_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    confidence_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    document: Mapped[Document] = relationship(back_populates="extracted_values")
    field: Mapped[ExtractionField] = relationship(back_populates="extracted_values")


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
    key_topics: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    document: Mapped[Document] = relationship(back_populates="summary")


class BulkJob(Base):
    """Bulk processing job tracking."""

    __tablename__ = "bulk_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'"), index=True
    )
    total_documents: Mapped[int] = mapped_column(Integer, nullable=False)
    processed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    documents: Mapped[list["BulkJobDocument"]] = relationship(back_populates="job")


class BulkJobDocument(Base):
    """Per-document status within a bulk job."""

    __tablename__ = "bulk_job_documents"
    __table_args__ = (
        UniqueConstraint("job_id", "document_id", name="uq_bulk_job_documents_job_doc"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bulk_jobs.id"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'")
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    job: Mapped[BulkJob] = relationship(back_populates="documents")
    document: Mapped[Document] = relationship(back_populates="bulk_job_documents")


class ConversationSummary(TimestampMixin, Base):
    """Persistent conversation summaries for long-term memory."""

    __tablename__ = "conversation_summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    session_id: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_topics: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    documents_discussed: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'")
    )
    queries_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class MemoryEntry(TimestampMixin, Base):
    """Generic key-value store for long-term memory."""

    __tablename__ = "memory_entries"
    __table_args__ = (
        UniqueConstraint("namespace", "key", name="uq_memory_entries_ns_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    namespace: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(500), nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
