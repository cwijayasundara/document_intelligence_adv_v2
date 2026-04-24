"""Shared runner plumbing — dataset loading, run-record persistence, aggregation.

Each stage-specific runner in this package consumes this helper and only
needs to provide:

  1. A name (`STAGE`).
  2. The JSONL filename holding its golden dataset.
  3. An async `predict(example)` coroutine that calls the production LLM
     touchpoint and returns a dict shaped like the evaluator input.
  4. A list of `(evaluator_name, evaluator_callable)` — typically taken
     from `metric_based.ALL_EVALUATORS` and `llm_judge.ALL_EVALUATORS`.

The helper:
  - Loads + slices the JSONL.
  - Creates an `EvalRun` row and per-result rows.
  - Runs each evaluator on each example (sync or async).
  - Aggregates summary scores (mean of numeric scores).
  - Optionally pushes to LangSmith (if `LANGSMITH_API_KEY` is set).
"""

from __future__ import annotations

import inspect
import json
import logging
import math
import os
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

DATASETS_DIR = Path(__file__).resolve().parent.parent / "datasets"


Evaluator = Callable[[Any, Any], Any]


@dataclass
class Example:
    id: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    metadata: dict[str, Any]


@dataclass
class RunRecord:
    outputs: dict[str, Any]
    inputs: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


def _json_safe(value: Any) -> Any:
    """Coerce arbitrary payloads into a JSON-serialisable shape.

    The `eval_results.prediction/expected/criteria_breakdown` columns are JSONB,
    and Postgres rejects JSON with NaN/Inf or raw Python objects like LangChain
    `BaseMessage`. Runners can return those by accident (e.g. agentic RAG dumps
    its `messages` list), so normalise here as a safety net.
    """
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value
    # LangChain / Pydantic models expose a dict dumper.
    if hasattr(value, "model_dump"):
        try:
            return _json_safe(value.model_dump())
        except Exception:  # noqa: BLE001 — fall through to str() below.
            pass
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(v) for v in value]
    if hasattr(value, "isoformat"):  # datetime / date
        return value.isoformat()
    return str(value)


def _git_sha() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
        )
        return out.decode().strip()
    except Exception:
        return None


def load_examples(dataset_file: str, subset: int | None = None, tags: list[str] | None = None) -> list[Example]:
    path = DATASETS_DIR / dataset_file
    if not path.exists():
        raise FileNotFoundError(f"dataset not found: {path}")

    examples: list[Example] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            record = json.loads(line)
            if tags:
                rec_tags = set(record.get("tags") or [])
                if not any(t in rec_tags for t in tags):
                    continue
            ex_id = record.get("id") or f"anon_{len(examples)}"
            meta = {"tags": record.get("tags") or [], "notes": record.get("notes") or ""}
            inputs: dict[str, Any] = {}
            outputs: dict[str, Any] = {}
            for k, v in record.items():
                if k in {"id", "tags", "notes", "source"}:
                    continue
                if k.startswith("expected_") or k.startswith("reference_") or k == "pe_checklist":
                    outputs[k] = v
                else:
                    inputs[k] = v
            examples.append(Example(id=ex_id, inputs=inputs, outputs=outputs, metadata=meta))

    if subset is not None:
        examples = examples[:subset]
    return examples


async def _invoke_evaluator(fn: Evaluator, run: RunRecord, example: Example) -> dict[str, Any]:
    if inspect.iscoroutinefunction(fn):
        result = await fn(run, example)
    else:
        result = fn(run, example)
    if inspect.isawaitable(result):
        result = await result
    return dict(result or {})


async def run_experiment(
    stage: str,
    dataset_file: str,
    predict: Callable[[Example], Awaitable[dict[str, Any]]],
    evaluators: list[tuple[str, Evaluator]],
    subset: int | None = None,
    tags: list[str] | None = None,
    model: str | None = None,
    judge_model: str | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Run one stage's experiment end-to-end.

    Returns a result dict:
        {
            "run_id": "...",
            "stage": "extraction",
            "total_examples": 15,
            "duration_seconds": 42.0,
            "summary_scores": {"extraction_exact_match": 0.87, ...},
        }
    """
    examples = load_examples(dataset_file, subset=subset, tags=tags)
    logger.info("stage=%s loaded %d examples from %s", stage, len(examples), dataset_file)

    start = time.time()

    run_id: uuid.UUID | None = None
    repo = None
    run_row = None
    session = None
    engine_initialised = False
    if persist:
        try:
            from src.config.settings import get_settings
            from src.db.connection import get_session_factory, init_engine
            from src.db.repositories.evals_repo import EvalRunRepository

            settings = get_settings()
            init_engine(settings.database_url, pool_size=2, max_overflow=1)
            engine_initialised = True
            factory = get_session_factory()
            session = factory()
            repo = EvalRunRepository(session)
            run_row = await repo.create_run(
                stage=stage,
                dataset_name=f"pe-doc-intel/{stage}",
                model=model or os.environ.get("OPENAI_MODEL", "unknown"),
                judge_model=judge_model,
                git_sha=_git_sha(),
                tags=tags or [],
            )
            await session.commit()
            run_id = run_row.id
        except Exception as exc:  # noqa: BLE001 — DB isn't always available (CI, dev).
            logger.warning("eval persistence disabled: %s", exc)
            persist = False
            repo = None
            if session is not None:
                try:
                    await session.close()
                except Exception:
                    logger.exception("failed to close db session during persistence setup")
                session = None

    try:
        summary_scores: dict[str, list[float]] = {}
        per_example_results: list[dict[str, Any]] = []

        for ex in examples:
            try:
                prediction_outputs = await predict(ex)
            except Exception as exc:  # noqa: BLE001 — record the failure, keep going.
                logger.exception("predict() failed for example %s", ex.id)
                prediction_outputs = {"error": str(exc)}

            run = RunRecord(outputs=prediction_outputs, inputs=ex.inputs, metadata=ex.metadata)
            per_example: dict[str, Any] = {"example_id": ex.id, "scores": {}}

            for key, fn in evaluators:
                try:
                    result = await _invoke_evaluator(fn, run, ex)
                except Exception as exc:  # noqa: BLE001 — one evaluator shouldn't kill the run.
                    logger.exception("evaluator=%s example=%s failed", key, ex.id)
                    result = {"key": key, "score": None, "comment": f"error: {exc}"}

                per_example["scores"][result.get("key", key)] = result
                raw_score = result.get("score")
                numeric_score: float | None = None
                if isinstance(raw_score, (int, float)):
                    f = float(raw_score)
                    # JSON can't represent NaN/Inf and Postgres JSONB rejects them.
                    # Treat non-finite as "no score" rather than propagating poison.
                    if math.isfinite(f):
                        numeric_score = f
                        summary_scores.setdefault(result.get("key", key), []).append(f)
                    else:
                        logger.warning(
                            "evaluator=%s example=%s returned non-finite score (%s); dropping",
                            key, ex.id, raw_score,
                        )

                if persist and repo and run_row:
                    await repo.add_result(
                        run_id=run_row.id,
                        example_id=ex.id,
                        evaluator_key=result.get("key", key),
                        score=numeric_score,
                        comment=str(result.get("comment", "")),
                        prediction=_json_safe(prediction_outputs),
                        expected=_json_safe(ex.outputs),
                        criteria_breakdown=_json_safe(result.get("criteria")),
                    )

            per_example_results.append(per_example)

        duration = time.time() - start
        summary = {
            k: round(sum(v) / len(v), 4)
            for k, v in summary_scores.items()
            if v and all(math.isfinite(x) for x in v)
        }

        if persist and repo and run_row and session is not None:
            await repo.finalise_run(
                run_row,
                total_examples=len(examples),
                duration_seconds=round(duration, 2),
                summary_scores=summary,
                status="completed",
            )
            await session.commit()

        return {
            "run_id": str(run_id) if run_id else None,
            "stage": stage,
            "total_examples": len(examples),
            "duration_seconds": round(duration, 2),
            "summary_scores": summary,
            "per_example": per_example_results,
        }
    except BaseException:
        if persist and repo and run_row and session is not None:
            try:
                await session.rollback()
                await repo.finalise_run(
                    run_row,
                    total_examples=len(examples),
                    duration_seconds=round(time.time() - start, 2),
                    summary_scores={},
                    status="failed",
                )
                await session.commit()
            except Exception:
                logger.exception("failed to record failed-run status")
        raise
    finally:
        if session is not None:
            try:
                await session.close()
            except Exception:
                logger.exception("failed to close db session")
        if engine_initialised:
            try:
                from src.db.connection import dispose_engine

                await dispose_engine()
            except Exception:
                logger.exception("failed to dispose db engine")
