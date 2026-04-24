"""Text-to-SQL runner — grades data agent SQL + chart + intent."""

from __future__ import annotations

from typing import Any

from ._base import Example, run_experiment as _run_experiment


async def _predict(example: Example) -> dict[str, Any]:
    from src.config.settings import get_settings
    from src.data_agent.agent import run_analytics_query
    from src.db.connection import get_session_factory, init_engine

    settings = get_settings()
    init_engine(settings.database_url, pool_size=2, max_overflow=1)
    factory = get_session_factory()
    async with factory() as session:
        try:
            response = await run_analytics_query(
                question=example.inputs.get("question", ""), session=session
            )
        except Exception as exc:  # noqa: BLE001 — refusal case is valid.
            return {"sql": "", "error": str(exc), "explanation": ""}
    return {
        "sql": response.get("sql", ""),
        "data": response.get("data"),
        "chart": response.get("chart"),
        "explanation": response.get("explanation", ""),
    }


def _evaluators() -> list[tuple[str, Any]]:
    import os

    from evals.evaluators.sql import (
        chart_shape,
        sql_contains_keywords,
        sql_rejected_as_expected,
        sql_safety,
        sql_validity,
    )

    evs: list[tuple[str, Any]] = [
        ("sql_validity", sql_validity),
        ("sql_safety", sql_safety),
        ("sql_rejected_as_expected", sql_rejected_as_expected),
        ("sql_contains_keywords", sql_contains_keywords),
        ("chart_shape", chart_shape),
    ]
    if os.environ.get("OPENAI_API_KEY"):
        from evals.evaluators.llm_judge import sql_intent_match
        from evals.evaluators.rubric import make_rubric_evaluator

        evs.append(("sql_intent_match", sql_intent_match))
        evs.append(("rubric_sql", make_rubric_evaluator("sql", context_keys=["question"])))
    return evs


async def run_experiment_wrapper(
    subset: int | None = None,
    tags: list[str] | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    return await _run_experiment(
        stage="sql",
        dataset_file="sql_golden.jsonl",
        predict=_predict,
        evaluators=_evaluators(),
        subset=subset,
        tags=tags,
        model=model,
    )


run_experiment = run_experiment_wrapper  # alias for CLI discovery
