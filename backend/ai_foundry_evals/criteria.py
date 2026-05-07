"""Builders for Azure Foundry testing_criteria dicts.

Each function returns a single criterion entry suitable for the
client.evals.create(testing_criteria=...) call.

Only evaluators that the existing backend/evals/ framework does not cover
are exported. Groundedness / Relevance / Retrieval are intentionally omitted
- the existing llm_judge/{faithfulness,relevance,ragas_triad}.py already
covers those. Coherence / Fluency / textual-similarity are likewise
intentionally omitted (covered by rubrics + metric_based).
"""

from __future__ import annotations

from typing import Any

from .settings import load_settings


def _builtin(
    name: str,
    evaluator_name: str,
    data_mapping: dict[str, str],
    *,
    needs_deployment: bool = True,
    init: dict[str, Any] | None = None,
) -> dict[str, Any]:
    spec: dict[str, Any] = {
        "type": "azure_ai_evaluator",
        "name": name,
        "evaluator_name": evaluator_name,
        "data_mapping": data_mapping,
    }
    init_params = dict(init or {})
    if needs_deployment:
        init_params.setdefault("deployment_name", load_settings().model_deployment)
    if init_params:
        spec["initialization_parameters"] = init_params
    return spec


# ---------- Risk & safety (Microsoft-hosted; no deployment_name) ----------

_QR = {"query": "{{item.query}}", "response": "{{item.response}}"}


def violence() -> dict[str, Any]:
    return _builtin("violence", "builtin.violence", _QR, needs_deployment=False)


def sexual() -> dict[str, Any]:
    return _builtin("sexual", "builtin.sexual", _QR, needs_deployment=False)


def self_harm() -> dict[str, Any]:
    return _builtin("self_harm", "builtin.self_harm", _QR, needs_deployment=False)


def hate_unfairness() -> dict[str, Any]:
    return _builtin("hate_unfairness", "builtin.hate_unfairness", _QR, needs_deployment=False)


def protected_material() -> dict[str, Any]:
    return _builtin("protected_material", "builtin.protected_material", _QR, needs_deployment=False)


def indirect_attack() -> dict[str, Any]:
    return _builtin("indirect_attack", "builtin.indirect_attack", _QR, needs_deployment=False)


def code_vulnerability() -> dict[str, Any]:
    return _builtin("code_vulnerability", "builtin.code_vulnerability", _QR, needs_deployment=False)


def ungrounded_attributes() -> dict[str, Any]:
    return _builtin(
        "ungrounded_attributes",
        "builtin.ungrounded_attributes",
        {**_QR, "context": "{{item.context}}"},
        needs_deployment=False,
    )


SAFETY_ALL: list[Any] = [
    violence,
    sexual,
    self_harm,
    hate_unfairness,
    protected_material,
    indirect_attack,
    code_vulnerability,
    ungrounded_attributes,
]


# ---------- Agent (LLM-judge; require deployment_name) ----------


def task_adherence() -> dict[str, Any]:
    return _builtin("task_adherence", "builtin.task_adherence", _QR)


def intent_resolution() -> dict[str, Any]:
    return _builtin("intent_resolution", "builtin.intent_resolution", _QR)


def tool_call_accuracy() -> dict[str, Any]:
    return _builtin(
        "tool_call_accuracy",
        "builtin.tool_call_accuracy",
        {**_QR, "tool_definitions": "{{item.tool_definitions}}"},
    )


def tool_selection() -> dict[str, Any]:
    return _builtin(
        "tool_selection",
        "builtin.tool_selection",
        {**_QR, "tool_definitions": "{{item.tool_definitions}}"},
    )


def task_navigation_efficiency(matching_mode: str = "in_order_match") -> dict[str, Any]:
    return _builtin(
        "task_navigation_efficiency",
        "builtin.task_navigation_efficiency",
        {
            "actions": "{{item.actions}}",
            "expected_actions": "{{item.expected_actions}}",
        },
        needs_deployment=False,
        init={"matching_mode": matching_mode},
    )


AGENT_ALL: list[Any] = [
    task_adherence,
    intent_resolution,
    tool_call_accuracy,
    tool_selection,
]


# ---------- Retrieval composite ----------


def document_retrieval(label_min: int = 0, label_max: int = 4) -> dict[str, Any]:
    return _builtin(
        "document_retrieval",
        "builtin.document_retrieval",
        {
            "retrieval_ground_truth": "{{item.retrieval_ground_truth}}",
            "retrieved_documents": "{{item.retrieved_documents}}",
        },
        needs_deployment=False,
        init={
            "ground_truth_label_min": label_min,
            "ground_truth_label_max": label_max,
        },
    )
