"""Submit a Foundry evaluation run and fetch results.

Mirrors `backend/evals/runners/_base.py` in spirit but talks to Foundry's
`client.evals.*` API instead of running evaluators in-process.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from ..client import get_evals_client

logger = logging.getLogger(__name__)


@dataclass
class FoundryRunResult:
    eval_id: str
    run_id: str
    status: str
    report_url: str | None
    items: list[dict[str, Any]]


def _infer_item_schema(rows: list[dict[str, Any]]) -> dict[str, Any]:
    keys = sorted({k for row in rows for k in row.keys()})
    properties: dict[str, dict[str, str]] = {}
    for k in keys:
        sample = next((row[k] for row in rows if k in row and row[k] is not None), None)
        if isinstance(sample, list):
            properties[k] = {"type": "array"}
        elif isinstance(sample, dict):
            properties[k] = {"type": "object"}
        elif isinstance(sample, bool):
            properties[k] = {"type": "boolean"}
        elif isinstance(sample, int):
            properties[k] = {"type": "integer"}
        elif isinstance(sample, float):
            properties[k] = {"type": "number"}
        else:
            properties[k] = {"type": "string"}
    return {"type": "object", "properties": properties}


def _build_jsonl_data_source(rows: list[dict[str, Any]]) -> Any:
    from openai.types.evals.create_eval_jsonl_run_data_source_param import (
        CreateEvalJSONLRunDataSourceParam,
        SourceFileContent,
        SourceFileContentContent,
    )

    return CreateEvalJSONLRunDataSourceParam(
        type="jsonl",
        source=SourceFileContent(
            type="file_content",
            content=[SourceFileContentContent(item=row) for row in rows],
        ),
    )


async def submit(
    *,
    name: str,
    rows: list[dict[str, Any]],
    testing_criteria: list[dict[str, Any]],
    item_schema: dict[str, Any] | None = None,
    poll_seconds: int = 5,
) -> FoundryRunResult:
    """Create eval, submit run, poll until done, and return per-item results."""
    from openai.types.eval_create_params import DataSourceConfigCustom

    if not rows:
        raise ValueError("submit() requires at least one row")
    if not testing_criteria:
        raise ValueError("submit() requires at least one testing criterion")

    client = get_evals_client()
    schema = item_schema or _infer_item_schema(rows)
    data_source_config = DataSourceConfigCustom(type="custom", item_schema=schema)

    eval_obj = client.evals.create(
        name=name,
        data_source_config=data_source_config,
        testing_criteria=testing_criteria,
    )
    run = client.evals.runs.create(
        eval_id=eval_obj.id,
        name=f"{name}-{int(time.time())}",
        data_source=_build_jsonl_data_source(rows),
    )

    while True:
        run = client.evals.runs.retrieve(run_id=run.id, eval_id=eval_obj.id)
        if run.status in ("completed", "failed"):
            break
        await asyncio.sleep(poll_seconds)

    items: list[dict[str, Any]] = []
    for it in client.evals.runs.output_items.list(run_id=run.id, eval_id=eval_obj.id):
        if hasattr(it, "model_dump"):
            items.append(it.model_dump())
        else:
            items.append(dict(it))

    return FoundryRunResult(
        eval_id=eval_obj.id,
        run_id=run.id,
        status=run.status,
        report_url=getattr(run, "report_url", None),
        items=items,
    )
