"""ORM models for eval runs, examples, and per-evaluator results.

An eval RUN is one execution of one pipeline STAGE against a named DATASET
using a specific MODEL. Each run contains N per-example RESULT rows, one
per example × evaluator pair.

These tables back the `/evals` dashboard — last-run scorecards, trend
charts, and run-detail drill-downs come from queries against these rows.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models.base import Base, TimestampMixin


class EvalRun(TimestampMixin, Base):
    """A single execution of one stage's eval experiment."""

    __tablename__ = "eval_runs"
    __table_args__ = (Index("ix_eval_runs_stage_created", "stage", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    stage: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    dataset_name: Mapped[str] = mapped_column(String(200), nullable=False)
    dataset_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    judge_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    git_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    total_examples: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    langsmith_experiment_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'running'"), index=True
    )  # running | completed | failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_scores: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        server_default=text("'{}'::jsonb"),
    )
    tags: Mapped[list | None] = mapped_column(
        JSONB, nullable=True, server_default=text("'[]'::jsonb")
    )

    results: Mapped[list["EvalResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class EvalResult(Base):
    """One per-example × per-evaluator score inside a run."""

    __tablename__ = "eval_results"
    __table_args__ = (Index("ix_eval_results_run_evaluator", "run_id", "evaluator_key"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("eval_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    example_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    evaluator_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    passed: Mapped[bool | None] = mapped_column(nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    prediction: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    expected: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    criteria_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    run: Mapped[EvalRun] = relationship(back_populates="results")
