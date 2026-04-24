"""Classification runner — grades `classify_document()` against classification_golden.jsonl."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ._base import Example, run_experiment as _run_experiment

logger = logging.getLogger(__name__)


async def _predict(example: Example) -> dict[str, Any]:
    from src.graph_nodes.classifier import classify_document

    inputs = example.inputs
    parsed_path = inputs.get("parsed_path")
    if parsed_path:
        content = Path(parsed_path).read_text() if Path(parsed_path).exists() else ""
    else:
        content = inputs.get("inline_content") or ""

    categories = inputs.get("categories") or _default_categories()
    result = await classify_document(
        file_name=inputs.get("file_name", "unknown.pdf"),
        content=content,
        categories=categories,
    )
    return {
        "category_id": str(result.category_id),
        "category_name": result.category_name,
        "confidence": int(result.confidence),
        "reasoning": result.reasoning,
    }


def _default_categories() -> list[dict[str, Any]]:
    import uuid

    return [
        {
            "id": uuid.uuid4(),
            "name": "Limited Partnership Agreement",
            "classification_criteria": "Fund name, GP/LP structure, management fee, carry, preferred return.",
        },
        {
            "id": uuid.uuid4(),
            "name": "Subscription Agreement",
            "classification_criteria": "Capital commitment + investor representations.",
        },
        {
            "id": uuid.uuid4(),
            "name": "Side Letter",
            "classification_criteria": "References a specific LPA; MFN, fee discounts, co-invest rights.",
        },
        {"id": uuid.uuid4(), "name": "Other", "classification_criteria": "Anything else."},
    ]


def _evaluators() -> list[tuple[str, Any]]:
    from evals.evaluators.metric_based import (
        classification_accuracy,
        classification_confidence_in_range,
    )

    return [
        ("classification_accuracy", classification_accuracy),
        ("classification_confidence_in_range", classification_confidence_in_range),
    ]


async def run_experiment_wrapper(
    subset: int | None = None,
    tags: list[str] | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    return await _run_experiment(
        stage="classification",
        dataset_file="classification_golden.jsonl",
        predict=_predict,
        evaluators=_evaluators(),
        subset=subset,
        tags=tags,
        model=model,
    )


# CLI hook — evals.cli imports `run_experiment` by this name.
run_experiment = run_experiment_wrapper  # alias for CLI discovery
