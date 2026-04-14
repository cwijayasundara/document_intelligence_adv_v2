"""Add pipeline tracking columns to documents table.

Revision ID: 003
Revises: 002a
Create Date: 2026-04-13
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "003"
down_revision = "002a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Widen status column for new longer status values
    op.alter_column(
        "documents",
        "status",
        type_=sa.String(50),
        existing_type=sa.String(20),
    )
    op.add_column(
        "documents",
        sa.Column(
            "pipeline_node_status",
            JSONB,
            nullable=True,
            server_default=sa.text("'{}'"),
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "pipeline_thread_id",
            sa.String(100),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("documents", "pipeline_thread_id")
    op.drop_column("documents", "pipeline_node_status")
