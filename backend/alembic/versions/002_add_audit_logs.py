"""Add audit_logs table.

Revision ID: 002
Revises: 001
Create Date: 2026-04-04
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("event_type", sa.String(50), nullable=False, index=True),
        sa.Column("entity_type", sa.String(30), nullable=False, index=True),
        sa.Column("entity_id", sa.String(36), nullable=True, index=True),
        sa.Column("document_id", sa.String(36), nullable=True, index=True),
        sa.Column("file_name", sa.String(500), nullable=True),
        sa.Column("details", JSONB, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
