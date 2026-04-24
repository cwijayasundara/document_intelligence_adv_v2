"""Add eval_runs and eval_results tables.

Revision ID: 004
Revises: 003
Create Date: 2026-04-23
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eval_runs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("stage", sa.String(32), nullable=False, index=True),
        sa.Column("dataset_name", sa.String(200), nullable=False),
        sa.Column("dataset_version", sa.String(40), nullable=True),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("judge_model", sa.String(120), nullable=True),
        sa.Column("git_sha", sa.String(64), nullable=True),
        sa.Column("total_examples", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("langsmith_experiment_url", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'running'"),
            index=True,
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("summary_scores", JSONB, nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column("tags", JSONB, nullable=True, server_default=sa.text("'[]'::jsonb")),
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
    op.create_index("ix_eval_runs_stage_created", "eval_runs", ["stage", "created_at"])

    op.create_table(
        "eval_results",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("eval_runs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("example_id", sa.String(200), nullable=False, index=True),
        sa.Column("evaluator_key", sa.String(80), nullable=False, index=True),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("passed", sa.Boolean, nullable=True),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("prediction", JSONB, nullable=True),
        sa.Column("expected", JSONB, nullable=True),
        sa.Column("criteria_breakdown", JSONB, nullable=True),
        sa.Column("created_at_ms", sa.Integer, nullable=True),
    )
    op.create_index("ix_eval_results_run_evaluator", "eval_results", ["run_id", "evaluator_key"])


def downgrade() -> None:
    op.drop_index("ix_eval_results_run_evaluator", table_name="eval_results")
    op.drop_table("eval_results")
    op.drop_index("ix_eval_runs_stage_created", table_name="eval_runs")
    op.drop_table("eval_runs")
