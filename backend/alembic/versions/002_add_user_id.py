"""Add user_id column to user-owned tables.

Revision ID: 002
Revises: 001
Create Date: 2026-03-30
"""

import sqlalchemy as sa

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add user_id (String 200, nullable, indexed) to user-owned tables."""

    # Add user_id to documents
    op.add_column("documents", sa.Column("user_id", sa.String(200), nullable=True))
    op.create_index("ix_documents_user_id", "documents", ["user_id"])

    # Add user_id to bulk_jobs
    op.add_column("bulk_jobs", sa.Column("user_id", sa.String(200), nullable=True))
    op.create_index("ix_bulk_jobs_user_id", "bulk_jobs", ["user_id"])

    # Add user_id to conversation_summaries
    op.add_column("conversation_summaries", sa.Column("user_id", sa.String(200), nullable=True))
    op.create_index("ix_conversation_summaries_user_id", "conversation_summaries", ["user_id"])

    # Drop unique constraint on session_id, replace with composite (user_id, session_id)
    op.drop_constraint(
        "conversation_summaries_session_id_key",
        "conversation_summaries",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_conversation_summaries_user_session",
        "conversation_summaries",
        ["user_id", "session_id"],
    )

    # Add user_id to memory_entries
    op.add_column("memory_entries", sa.Column("user_id", sa.String(200), nullable=True))
    op.create_index("ix_memory_entries_user_id", "memory_entries", ["user_id"])


def downgrade() -> None:
    """Remove user_id columns from user-owned tables."""

    # memory_entries
    op.drop_index("ix_memory_entries_user_id", "memory_entries")
    op.drop_column("memory_entries", "user_id")

    # conversation_summaries
    op.drop_constraint(
        "uq_conversation_summaries_user_session",
        "conversation_summaries",
        type_="unique",
    )
    op.create_unique_constraint(
        "conversation_summaries_session_id_key",
        "conversation_summaries",
        ["session_id"],
    )
    op.drop_index("ix_conversation_summaries_user_id", "conversation_summaries")
    op.drop_column("conversation_summaries", "user_id")

    # bulk_jobs
    op.drop_index("ix_bulk_jobs_user_id", "bulk_jobs")
    op.drop_column("bulk_jobs", "user_id")

    # documents
    op.drop_index("ix_documents_user_id", "documents")
    op.drop_column("documents", "user_id")
