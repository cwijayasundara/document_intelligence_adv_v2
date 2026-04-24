"""Eval dashboard API — list runs, fetch detail, trigger runs, stream progress.

Frontend calls:
    GET  /api/v1/evals/overview         → scorecards per stage.
    GET  /api/v1/evals/runs             → paginated run list.
    GET  /api/v1/evals/runs/{id}        → one run + its results.
    POST /api/v1/evals/runs             → trigger a run (fire-and-forget).
    GET  /api/v1/evals/trends           → time-series for a metric.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_session
from src.db.repositories.evals_repo import EvalRunRepository

logger = logging.getLogger(__name__)
router = APIRouter()

STAGE_CHOICES = [
    "classification",
    "extraction",
    "summary",
    "rag",
    "sql",
    "agentic_rag",
    "pipeline",
]


class EvalRunItem(BaseModel):
    id: uuid.UUID
    stage: str
    dataset_name: str
    dataset_version: str | None = None
    model: str
    judge_model: str | None = None
    git_sha: str | None = None
    total_examples: int
    duration_seconds: float | None = None
    status: str
    summary_scores: dict[str, float] = Field(default_factory=dict)
    langsmith_experiment_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class EvalResultItem(BaseModel):
    example_id: str
    evaluator_key: str
    score: float | None
    passed: bool | None = None
    comment: str | None = None
    prediction: dict | None = None
    expected: dict | None = None
    criteria_breakdown: dict | None = None


class EvalRunDetail(BaseModel):
    run: EvalRunItem
    results: list[EvalResultItem] = Field(default_factory=list)


class OverviewItem(BaseModel):
    stage: str
    run: EvalRunItem | None = None
    primary_score: float | None = None
    primary_metric_key: str | None = None
    delta_vs_previous: float | None = None


class TriggerRunRequest(BaseModel):
    stage: str
    subset: int | None = None
    tags: list[str] | None = None
    model: str | None = None


class TrendPoint(BaseModel):
    run_id: uuid.UUID
    created_at: datetime
    score: float | None


class TrendResponse(BaseModel):
    stage: str
    evaluator_key: str
    points: list[TrendPoint]


_PRIMARY_METRIC = {
    "classification": "classification_accuracy",
    "extraction": "extraction_exact_match",
    "summary": "summary_pe_checklist_coverage",
    "rag": "rag_answer_contains",
    "sql": "sql_validity",
    # `trajectory_subset` requires `expected_tools` in the dataset, which the
    # shared `rag_golden.jsonl` does not provide — so it returns None for every
    # example and drops out of summary_scores. Use `rag_answer_contains` which
    # always fires when `expected_answer_contains` is set.
    "agentic_rag": "rag_answer_contains",
    "pipeline": "pipeline_stages_subset",
}


def _primary_for(stage: str) -> str:
    return _PRIMARY_METRIC.get(stage, "score")


def _resolve_primary(
    stage: str, summary_scores: dict[str, float] | None
) -> tuple[str | None, float | None]:
    """Pick the best (key, score) to show as the stage's headline number.

    Prefers the stage's designated primary metric. Falls back to the
    alphabetically-first non-None score in `summary_scores` so a missing
    primary metric doesn't silently render as 0%.
    """
    scores = summary_scores or {}
    preferred = _primary_for(stage)
    if preferred in scores and scores[preferred] is not None:
        return preferred, scores[preferred]
    for key in sorted(scores):
        value = scores[key]
        if isinstance(value, (int, float)):
            return key, float(value)
    return None, None


@router.get("/evals/overview", response_model=list[OverviewItem])
async def get_overview(session: AsyncSession = Depends(get_session)) -> list[OverviewItem]:
    repo = EvalRunRepository(session)
    latest = await repo.latest_run_per_stage()
    by_stage: dict[str, Any] = {run.stage: run for run in latest}

    out: list[OverviewItem] = []
    for stage in STAGE_CHOICES:
        run = by_stage.get(stage)
        if run is None:
            out.append(OverviewItem(stage=stage))
            continue

        metric_key, primary_score = _resolve_primary(stage, run.summary_scores)
        # Compare against the same metric_key we chose for the current run,
        # so the delta is meaningful even when we fell back to a secondary.
        delta = None
        if metric_key is not None:
            prev_runs = await repo.list_runs(stage=stage, limit=2, offset=1)
            prev_score = (
                (prev_runs[0].summary_scores or {}).get(metric_key) if prev_runs else None
            )
            if primary_score is not None and prev_score is not None:
                delta = primary_score - prev_score
        out.append(
            OverviewItem(
                stage=stage,
                run=EvalRunItem.model_validate(run),
                primary_score=primary_score,
                primary_metric_key=metric_key,
                delta_vs_previous=delta,
            )
        )
    return out


@router.get("/evals/runs", response_model=list[EvalRunItem])
async def list_runs(
    stage: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[EvalRunItem]:
    repo = EvalRunRepository(session)
    rows = await repo.list_runs(stage=stage, limit=limit, offset=offset)
    return [EvalRunItem.model_validate(r) for r in rows]


@router.get("/evals/runs/{run_id}", response_model=EvalRunDetail)
async def get_run(run_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> EvalRunDetail:
    repo = EvalRunRepository(session)
    row = await repo.get_run(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="run not found")
    results = await repo.get_results(run_id)
    return EvalRunDetail(
        run=EvalRunItem.model_validate(row),
        results=[
            EvalResultItem(
                example_id=r.example_id,
                evaluator_key=r.evaluator_key,
                score=r.score,
                passed=r.passed,
                comment=r.comment,
                prediction=r.prediction,
                expected=r.expected,
                criteria_breakdown=r.criteria_breakdown,
            )
            for r in results
        ],
    )


@router.post("/evals/runs", status_code=202)
async def trigger_run(body: TriggerRunRequest, background: BackgroundTasks) -> dict[str, str]:
    if body.stage not in STAGE_CHOICES:
        raise HTTPException(status_code=400, detail=f"unknown stage '{body.stage}'")

    async def _execute() -> None:
        module_name = f"backend.evals.runners.run_{body.stage}"
        try:
            module = __import__(module_name, fromlist=["run_experiment"])
            runner = getattr(module, "run_experiment")
            await runner(subset=body.subset, tags=body.tags, model=body.model)
        except Exception:  # noqa: BLE001 — background task errors are logged only.
            logger.exception("background eval run failed stage=%s", body.stage)

    background.add_task(asyncio.create_task, _execute())
    return {"status": "accepted", "stage": body.stage}


@router.get("/evals/trends", response_model=TrendResponse)
async def get_trend(
    stage: str = Query(...),
    evaluator_key: str = Query(...),
    limit: int = Query(50, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> TrendResponse:
    repo = EvalRunRepository(session)
    rows = await repo.trend(stage=stage, evaluator_key=evaluator_key, limit=limit)
    return TrendResponse(
        stage=stage,
        evaluator_key=evaluator_key,
        points=[TrendPoint(run_id=r, created_at=c, score=s) for (r, c, s) in rows],
    )
