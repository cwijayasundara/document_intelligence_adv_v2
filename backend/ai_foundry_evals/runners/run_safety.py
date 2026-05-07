"""Run all Azure safety evaluators against a stage's outputs.

Reuses the existing `_predict` from `evals.runners.run_*` so we don't
duplicate the production-call logic. For each example: predict, adapt to
{query, response, context}, then submit one Foundry run with all 8 safety
criteria.
"""

from __future__ import annotations

import logging
import time
from importlib import import_module
from typing import Any

from ..adapter import to_safety_row
from ..criteria import (
    code_vulnerability,
    hate_unfairness,
    indirect_attack,
    protected_material,
    self_harm,
    sexual,
    ungrounded_attributes,
    violence,
)
from ._base import FoundryRunResult, submit

logger = logging.getLogger(__name__)


_STAGE_PREDICT: dict[str, tuple[str, str, str]] = {
    "rag": ("evals.runners.run_rag", "_predict", "rag_golden.jsonl"),
    "summary": ("evals.runners.run_summary", "_predict", "summary_golden.jsonl"),
    "agentic_rag": ("evals.runners.run_agentic_rag", "_predict", "rag_golden.jsonl"),
}


async def run_safety(*, stage: str, subset: int | None = None) -> FoundryRunResult:
    if stage not in _STAGE_PREDICT:
        raise ValueError(f"unknown stage {stage!r}; valid: {sorted(_STAGE_PREDICT)}")

    module_name, fn_name, dataset = _STAGE_PREDICT[stage]
    from evals.runners._base import load_examples

    predict = getattr(import_module(module_name), fn_name)
    examples = load_examples(dataset, subset=subset)

    rows: list[dict[str, Any]] = []
    for ex in examples:
        try:
            outputs = await predict(ex)
        except Exception as exc:  # noqa: BLE001
            logger.exception("predict failed for %s/%s: %s", stage, ex.id, exc)
            outputs = {"answer": "", "summary": "", "error": str(exc)}
        rows.append(to_safety_row(ex.inputs, outputs))

    criteria = [
        violence(),
        sexual(),
        self_harm(),
        hate_unfairness(),
        protected_material(),
        indirect_attack(),
        code_vulnerability(),
        ungrounded_attributes(),
    ]
    return await submit(
        name=f"safety-{stage}-{int(time.time())}",
        rows=rows,
        testing_criteria=criteria,
    )
