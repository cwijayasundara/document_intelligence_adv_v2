"""Add extracted_value_citations table for bbox-level source highlights.

Revision ID: 005
Revises: 004
Create Date: 2026-05-08
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "extracted_value_citations",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "extracted_value_id",
            UUID(as_uuid=True),
            sa.ForeignKey("extracted_values.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("page", sa.Integer, nullable=False),
        sa.Column("bbox_left", sa.Float, nullable=False),
        sa.Column("bbox_top", sa.Float, nullable=False),
        sa.Column("bbox_width", sa.Float, nullable=False),
        sa.Column("bbox_height", sa.Float, nullable=False),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("confidence", sa.String(10), nullable=False, server_default=sa.text("'medium'")),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("extracted_value_citations")
