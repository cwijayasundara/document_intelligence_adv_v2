"""Initial schema: create all 10 tables.

Revision ID: 001
Revises:
Create Date: 2026-03-28
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all 10 tables for the PE Document Intelligence Platform."""

    # 1. document_categories (referenced by documents and extraction_schemas)
    op.create_table(
        "document_categories",
        sa.Column(
            "id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True
        ),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("classification_criteria", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # 2. documents
    op.create_table(
        "documents",
        sa.Column(
            "id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True
        ),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("original_path", sa.String(1000), nullable=False),
        sa.Column("parsed_path", sa.String(1000), nullable=True),
        sa.Column("file_hash", sa.String(64), nullable=False, index=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'uploaded'"),
            index=True,
        ),
        sa.Column(
            "document_category_id",
            UUID(as_uuid=True),
            sa.ForeignKey("document_categories.id"),
            nullable=True,
            index=True,
        ),
        sa.Column("file_type", sa.String(20), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # 3. extraction_schemas
    op.create_table(
        "extraction_schemas",
        sa.Column(
            "id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True
        ),
        sa.Column(
            "category_id",
            UUID(as_uuid=True),
            sa.ForeignKey("document_categories.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("schema_yaml", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "category_id", "version", name="uq_extraction_schemas_category_version"
        ),
    )

    # 4. extraction_fields
    op.create_table(
        "extraction_fields",
        sa.Column(
            "id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True
        ),
        sa.Column(
            "schema_id",
            UUID(as_uuid=True),
            sa.ForeignKey("extraction_schemas.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("field_name", sa.String(200), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("examples", sa.Text(), nullable=True),
        sa.Column("data_type", sa.String(20), nullable=False, server_default=sa.text("'string'")),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.UniqueConstraint("schema_id", "field_name", name="uq_extraction_fields_schema_field"),
    )

    # 5. extracted_values
    op.create_table(
        "extracted_values",
        sa.Column(
            "id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True
        ),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("documents.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "field_id",
            UUID(as_uuid=True),
            sa.ForeignKey("extraction_fields.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("extracted_value", sa.Text(), nullable=True),
        sa.Column("source_text", sa.Text(), nullable=True),
        sa.Column("confidence", sa.String(10), nullable=False),
        sa.Column("confidence_reasoning", sa.Text(), nullable=True),
        sa.Column("requires_review", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reviewed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("document_id", "field_id", name="uq_extracted_values_doc_field"),
    )

    # 6. document_summaries
    op.create_table(
        "document_summaries",
        sa.Column(
            "id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True
        ),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("documents.id"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("key_topics", JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # 7. bulk_jobs
    op.create_table(
        "bulk_jobs",
        sa.Column(
            "id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True
        ),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default=sa.text("'pending'"), index=True
        ),
        sa.Column("total_documents", sa.Integer(), nullable=False),
        sa.Column("processed_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 8. bulk_job_documents
    op.create_table(
        "bulk_job_documents",
        sa.Column(
            "id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True
        ),
        sa.Column(
            "job_id", UUID(as_uuid=True), sa.ForeignKey("bulk_jobs.id"), nullable=False, index=True
        ),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("documents.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.UniqueConstraint("job_id", "document_id", name="uq_bulk_job_documents_job_doc"),
    )

    # 9. conversation_summaries
    op.create_table(
        "conversation_summaries",
        sa.Column(
            "id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True
        ),
        sa.Column("session_id", sa.String(200), nullable=False, unique=True, index=True),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("key_topics", JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("documents_discussed", JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("queries_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # 10. memory_entries
    op.create_table(
        "memory_entries",
        sa.Column(
            "id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True
        ),
        sa.Column("namespace", sa.String(200), nullable=False, index=True),
        sa.Column("key", sa.String(500), nullable=False),
        sa.Column("data", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("namespace", "key", name="uq_memory_entries_ns_key"),
    )


def downgrade() -> None:
    """Drop all 10 tables in reverse order."""
    op.drop_table("memory_entries")
    op.drop_table("conversation_summaries")
    op.drop_table("bulk_job_documents")
    op.drop_table("bulk_jobs")
    op.drop_table("document_summaries")
    op.drop_table("extracted_values")
    op.drop_table("extraction_fields")
    op.drop_table("extraction_schemas")
    op.drop_table("documents")
    op.drop_table("document_categories")
