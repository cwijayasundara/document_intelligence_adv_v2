"""Summary runner — grades summarize_document() with checklist + faithfulness + rubric."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ._base import Example, run_experiment as _run_experiment


async def _predict(example: Example) -> dict[str, Any]:
    from src.graph_nodes.summarizer import summarize_document

    inputs = example.inputs
    parsed_path = inputs.get("parsed_path")
    if parsed_path and Path(parsed_path).exists():
        content = Path(parsed_path).read_text()
    else:
        content = inputs.get("inline_content") or ""

    result = await summarize_document(parsed_content=content)
    return {"summary": result.summary, "key_topics": list(result.key_topics)}


def _evaluators() -> list[tuple[str, Any]]:
    import os

    from evals.evaluators.metric_based import (
        summary_pe_checklist_coverage,
        summary_topic_count,
    )

    evs: list[tuple[str, Any]] = [
        ("summary_pe_checklist_coverage", summary_pe_checklist_coverage),
        ("summary_topic_count", summary_topic_count),
    ]
    if os.environ.get("OPENAI_API_KEY"):
        from evals.evaluators.llm_judge import summary_faithfulness
        from evals.evaluators.rubric import make_rubric_evaluator

        evs.append(("summary_faithfulness", summary_faithfulness))
        evs.append(
            (
                "rubric_summary",
                make_rubric_evaluator("summary", context_keys=["parsed_path", "inline_content"]),
            )
        )
    return evs


async def run_experiment_wrapper(
    subset: int | None = None,
    tags: list[str] | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    return await _run_experiment(
        stage="summary",
        dataset_file="summary_golden.jsonl",
        predict=_predict,
        evaluators=_evaluators(),
        subset=subset,
        tags=tags,
        model=model,
    )


run_experiment = run_experiment_wrapper  # alias for CLI discovery
