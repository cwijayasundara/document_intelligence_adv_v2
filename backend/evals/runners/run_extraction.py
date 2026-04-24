"""Extraction runner — grades extract_fields() + extraction source fidelity."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ._base import Example, run_experiment as _run_experiment

logger = logging.getLogger(__name__)


async def _predict(example: Example) -> dict[str, Any]:
    from src.graph_nodes.extractor import extract_fields

    inputs = example.inputs
    parsed_path = inputs.get("parsed_path")
    if parsed_path and Path(parsed_path).exists():
        content = Path(parsed_path).read_text()
    else:
        content = inputs.get("inline_content") or ""

    field_name = inputs.get("field_name")
    data_type = inputs.get("data_type", "string")
    fields_schema = [{"field_name": field_name, "data_type": data_type, "description": ""}]

    result = await extract_fields(parsed_content=content, extraction_fields=fields_schema)
    return {
        "fields": [
            {
                "field_name": f.field_name,
                "extracted_value": f.extracted_value,
                "source_text": f.source_text,
            }
            for f in result.fields
        ]
    }


def _evaluators() -> list[tuple[str, Any]]:
    from evals.evaluators.metric_based import (
        extraction_exact_match,
        extraction_numeric_tolerance,
        extraction_source_substring,
    )

    base = [
        ("extraction_exact_match", extraction_exact_match),
        ("extraction_numeric_tolerance", extraction_numeric_tolerance),
        ("extraction_source_substring", extraction_source_substring),
    ]

    # Source-fidelity judge is an LLM call — only wire if we have an API key.
    import os

    if os.environ.get("OPENAI_API_KEY"):
        from evals.evaluators.llm_judge import extraction_source_fidelity

        base.append(("extraction_source_fidelity", extraction_source_fidelity))
    return base


async def run_experiment_wrapper(
    subset: int | None = None,
    tags: list[str] | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    return await _run_experiment(
        stage="extraction",
        dataset_file="extraction_golden.jsonl",
        predict=_predict,
        evaluators=_evaluators(),
        subset=subset,
        tags=tags,
        model=model,
    )


run_experiment = run_experiment_wrapper  # alias for CLI discovery
