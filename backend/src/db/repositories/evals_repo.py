"""Repository for EvalRun / EvalResult CRUD."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.eval_run import EvalResult, EvalRun


class EvalRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(
        self,
        stage: str,
        dataset_name: str,
        model: str,
        dataset_version: str | None = None,
        judge_model: str | None = None,
        git_sha: str | None = None,
        tags: list[str] | None = None,
    ) -> EvalRun:
        run = EvalRun(
            stage=stage,
            dataset_name=dataset_name,
            dataset_version=dataset_version,
            model=model,
            judge_model=judge_model,
            git_sha=git_sha,
            tags=tags or [],
            status="running",
            total_examples=0,
            summary_scores={},
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def add_result(
        self,
        run_id: uuid.UUID,
        example_id: str,
        evaluator_key: str,
        score: float | None,
        comment: str,
        passed: bool | None = None,
        prediction: dict[str, Any] | None = None,
        expected: dict[str, Any] | None = None,
        criteria_breakdown: dict[str, Any] | None = None,
    ) -> EvalResult:
        row = EvalResult(
            run_id=run_id,
            example_id=example_id,
            evaluator_key=evaluator_key,
            score=score,
            passed=passed,
            comment=comment,
            prediction=prediction,
            expected=expected,
            criteria_breakdown=criteria_breakdown,
        )
        self.session.add(row)
        return row

    async def finalise_run(
        self,
        run: EvalRun,
        total_examples: int,
        duration_seconds: float,
        summary_scores: dict[str, Any],
        status: str = "completed",
        error_message: str | None = None,
        langsmith_experiment_url: str | None = None,
    ) -> EvalRun:
        run.total_examples = total_examples
        run.duration_seconds = duration_seconds
        run.summary_scores = summary_scores
        run.status = status
        run.error_message = error_message
        run.langsmith_experiment_url = langsmith_experiment_url
        run.updated_at = datetime.utcnow()
        await self.session.flush()
        return run

    async def list_runs(
        self,
        stage: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EvalRun]:
        stmt = select(EvalRun).order_by(desc(EvalRun.created_at)).limit(limit).offset(offset)
        if stage:
            stmt = stmt.where(EvalRun.stage == stage)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_run(self, run_id: uuid.UUID) -> EvalRun | None:
        stmt = select(EvalRun).where(EvalRun.id == run_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_results(
        self, run_id: uuid.UUID, evaluator_key: str | None = None
    ) -> list[EvalResult]:
        stmt = select(EvalResult).where(EvalResult.run_id == run_id)
        if evaluator_key:
            stmt = stmt.where(EvalResult.evaluator_key == evaluator_key)
        stmt = stmt.order_by(EvalResult.example_id, EvalResult.evaluator_key)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def latest_run_per_stage(self) -> list[EvalRun]:
        """One row per stage — the most recent completed run."""
        subq = (
            select(EvalRun.stage, func.max(EvalRun.created_at).label("max_ts"))
            .where(EvalRun.status == "completed")
            .group_by(EvalRun.stage)
            .subquery()
        )
        stmt = (
            select(EvalRun)
            .join(subq, (EvalRun.stage == subq.c.stage) & (EvalRun.created_at == subq.c.max_ts))
            .order_by(EvalRun.stage)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def trend(
        self, stage: str, evaluator_key: str, limit: int = 50
    ) -> list[tuple[uuid.UUID, datetime, float | None]]:
        """Time-series of `evaluator_key` scores for `stage` runs."""
        stmt = (
            select(EvalRun.id, EvalRun.created_at, EvalRun.summary_scores)
            .where(EvalRun.stage == stage)
            .where(EvalRun.status == "completed")
            .order_by(EvalRun.created_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        out: list[tuple[uuid.UUID, datetime, float | None]] = []
        for row in result.all():
            run_id, created_at, summary = row
            score = (summary or {}).get(evaluator_key)
            out.append((run_id, created_at, float(score) if score is not None else None))
        return out
