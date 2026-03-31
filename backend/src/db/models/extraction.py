"""Extraction ORM models: schemas, fields, and extracted values."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models.base import Base
from src.db.models.documents import Document


class ExtractionSchema(Base):
    """Versioned extraction field definitions per category."""

    __tablename__ = "extraction_schemas"
    __table_args__ = (
        UniqueConstraint(
            "category_id", "version", name="uq_extraction_schemas_category_version"
        ),
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
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    schema_yaml: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships (string refs resolved by SQLAlchemy mapper)
    category: Mapped[DocumentCategory] = relationship(
        back_populates="extraction_schemas"
    )
    fields: Mapped[list[ExtractionField]] = relationship(back_populates="schema")


class ExtractionField(Base):
    """Individual field definitions within an extraction schema."""

    __tablename__ = "extraction_fields"
    __table_args__ = (
        UniqueConstraint(
            "schema_id", "field_name", name="uq_extraction_fields_schema_field"
        ),
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
    required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )

    # Relationships
    schema: Mapped[ExtractionSchema] = relationship(back_populates="fields")
    extracted_values: Mapped[list[ExtractedValue]] = relationship(
        back_populates="field"
    )


class ExtractedValue(Base):
    """Extracted data per document per field, with confidence scoring."""

    __tablename__ = "extracted_values"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "field_id", name="uq_extracted_values_doc_field"
        ),
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
    reviewed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    document: Mapped[Document] = relationship(back_populates="extracted_values")
    field: Mapped[ExtractionField] = relationship(back_populates="extracted_values")
