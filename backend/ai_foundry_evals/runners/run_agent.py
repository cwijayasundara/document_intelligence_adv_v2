"""Run Azure agent evaluators against the agentic_rag pipeline.

Replaces the homegrown trajectory rubric with TaskAdherence, IntentResolution,
ToolCallAccuracy, and ToolSelection. TaskNavigationEfficiency is opt-in
because it requires `expected_actions` ground truth on each example.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from ..agent.message_adapter import langchain_tools_to_definitions, to_openai_messages
from ..criteria import (
    intent_resolution,
    task_adherence,
    task_navigation_efficiency,
    tool_call_accuracy,
    tool_selection,
)
from ._base import FoundryRunResult, submit

logger = logging.getLogger(__name__)


async def run_agent(
    *,
    subset: int | None = None,
    include_navigation_efficiency: bool = False,
    matching_mode: str = "in_order_match",
) -> FoundryRunResult:
    from evals.runners._base import load_examples
    from evals.runners.run_agentic_rag import _predict

    examples = load_examples("rag_golden.jsonl", subset=subset)
    tool_definitions = langchain_tools_to_definitions()
    if not tool_definitions:
        logger.warning(
            "tool_definitions is empty — tool_call_accuracy / tool_selection will "
            "still run but with reduced signal. Wire up langchain_tools_to_definitions()."
        )

    rows: list[dict[str, Any]] = []
    for ex in examples:
        try:
            outputs = await _predict(ex)
        except Exception as exc:  # noqa: BLE001
            logger.exception("agentic_rag predict failed for %s: %s", ex.id, exc)
            outputs = {"answer": "", "messages": [], "trajectory": []}

        all_msgs = to_openai_messages(outputs.get("messages") or [])
        first_assistant_idx = next(
            (i for i, m in enumerate(all_msgs) if m["role"] == "assistant"),
            len(all_msgs),
        )
        query_msgs = all_msgs[:first_assistant_idx] or [
            {"role": "user", "content": [{"type": "text", "text": ex.inputs.get("query", "")}]}
        ]
        response_msgs = all_msgs[first_assistant_idx:]

        row: dict[str, Any] = {
            "query": query_msgs,
            "response": response_msgs,
            "tool_definitions": tool_definitions,
        }
        if include_navigation_efficiency:
            row["actions"] = [m for m in response_msgs if m["role"] == "assistant"]
            row["expected_actions"] = (ex.outputs or {}).get("expected_tools") or []
        rows.append(row)

    criteria = [
        task_adherence(),
        intent_resolution(),
        tool_call_accuracy(),
        tool_selection(),
    ]
    if include_navigation_efficiency:
        criteria.append(task_navigation_efficiency(matching_mode=matching_mode))

    return await submit(
        name=f"agent-agentic_rag-{int(time.time())}",
        rows=rows,
        testing_criteria=criteria,
    )
