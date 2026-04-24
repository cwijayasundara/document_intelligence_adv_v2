"""End-to-end pipeline runner — gate routing + stage traversal.

Full graph execution would require seeded DB rows, real PDFs, and live Reducto
/ OpenAI calls, which is out of scope for a hermetic eval. Instead we verify
the two things that are actually decidable without that scaffolding:

  1. Gate routing — `route_after_parse` and `route_after_extract` are pure
     functions over `DocumentState`. Feed each golden example a synthesized
     state matching its documented profile and check the gates route to the
     branch the dataset declares.
  2. Graph traversal — given the two gate decisions, compute the deterministic
     node-visit order and compare against `expected_stages`.

If the gate implementation regresses (e.g. inverted comparison, wrong field),
the stages_reached list diverges and the eval fails. That is the scope
this runner signs up for — not end-to-end document intelligence.
"""

from __future__ import annotations

import logging
from typing import Any

from ._base import Example, run_experiment as _run_experiment

logger = logging.getLogger(__name__)

_PARSE_THRESHOLD_DEFAULT = 90.0


def _synthesize_state(example: Example) -> dict[str, Any]:
    """Build a minimal DocumentState that matches the example's profile.

    The golden data declares `expected_gates` and, optionally,
    `expected_min_parse_confidence`. We construct state fields so the two
    pure gate functions observe the documented conditions.
    """
    expected_gates = (example.outputs or {}).get("expected_gates") or {}
    parse_gate = expected_gates.get("parse_confidence_gate", "pass")
    extract_gate = expected_gates.get("extraction_review_gate", "pass")
    min_conf = float((example.outputs or {}).get("expected_min_parse_confidence", 80.0))

    # Parse confidence: if the golden says "pass", sit at the max of the
    # documented minimum and the default threshold; if "requires_review",
    # drop just below the threshold.
    if parse_gate == "pass":
        parse_conf = max(min_conf, _PARSE_THRESHOLD_DEFAULT)
    else:
        parse_conf = min(min_conf, _PARSE_THRESHOLD_DEFAULT - 1.0)

    # Extraction review: at least one field with requires_review flips the gate.
    extraction_results: list[dict[str, Any]] = [
        {"field_name": "management_fee_rate", "requires_review": extract_gate == "requires_review"},
    ]

    return {
        "document_id": example.inputs.get("doc_id") or example.id,
        "file_name": example.inputs.get("file_name", ""),
        "parse_confidence_pct": parse_conf,
        "extraction_results": extraction_results,
    }


def _traverse(state: dict[str, Any]) -> tuple[list[str], dict[str, str]]:
    """Deterministic walk through the compiled graph, recording node visits.

    Reimplements the edge layout in `src/bulk/pipeline.py` without invoking
    the nodes themselves. Changes to the edge layout will break this — which
    is what we want the eval to catch.
    """
    from src.bulk.gates import route_after_extract, route_after_parse

    stages: list[str] = ["parse"]
    after_parse = route_after_parse(state)
    if after_parse == "await_parse_review":
        stages.append("await_parse_review")
    stages.extend(["summarize", "classify", "extract"])
    after_extract = route_after_extract(state)
    if after_extract == "await_extraction_review":
        stages.append("await_extraction_review")
    stages.extend(["ingest", "finalize"])

    review_gate = {
        "parse_confidence_gate": "pass" if after_parse == "summarize" else "requires_review",
        "extraction_review_gate": "pass" if after_extract == "ingest" else "requires_review",
    }
    return stages, review_gate


async def _predict(example: Example) -> dict[str, Any]:
    """Exercise gate routing + graph traversal; no LLM / DB calls."""
    state = _synthesize_state(example)
    try:
        stages_reached, review_gate = _traverse(state)
    except Exception as exc:  # noqa: BLE001 — gate regression should grade as failure, not crash.
        logger.exception("pipeline gate traversal failed for example %s", example.id)
        return {"error": str(exc), "stages_reached": [], "review_gate": {}, "final_state": None}

    return {
        "stages_reached": stages_reached,
        "parse_confidence": state["parse_confidence_pct"],
        "review_gate": review_gate,
        "final_state": {
            "parse_confidence_pct": state["parse_confidence_pct"],
            "stages_reached": stages_reached,
            "review_gate_state": review_gate,
            "status": "completed",
        },
    }


def _expected_stages_subset(run: Any, example: Any) -> dict[str, Any]:
    required = (example.outputs or {}).get("expected_stages") or []
    actual = set((run.outputs or {}).get("stages_reached") or [])
    missing = [s for s in required if s not in actual]
    score = 1.0 if not missing else max(0.0, 1 - len(missing) / len(required))
    return {
        "key": "pipeline_stages_subset",
        "score": round(score, 3),
        "comment": f"missing={missing} actual={sorted(actual)}",
    }


def _gate_correctness(run: Any, example: Any) -> dict[str, Any]:
    expected = (example.outputs or {}).get("expected_gates") or {}
    actual_gate = (run.outputs or {}).get("review_gate") or {}
    mismatches: list[str] = []
    for gate_name, expected_state in expected.items():
        if actual_gate.get(gate_name) != expected_state:
            mismatches.append(f"{gate_name}: expected {expected_state}, got {actual_gate.get(gate_name)}")
    score = 1.0 if not mismatches else max(0.0, 1 - len(mismatches) / max(1, len(expected)))
    return {
        "key": "pipeline_gate_correctness",
        "score": round(score, 3),
        "comment": f"mismatches={mismatches}",
    }


def _evaluators() -> list[tuple[str, Any]]:
    return [
        ("pipeline_stages_subset", _expected_stages_subset),
        ("pipeline_gate_correctness", _gate_correctness),
    ]


async def run_experiment_wrapper(
    subset: int | None = None,
    tags: list[str] | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    return await _run_experiment(
        stage="pipeline",
        dataset_file="pipeline_golden.jsonl",
        predict=_predict,
        evaluators=_evaluators(),
        subset=subset,
        tags=tags,
        model=model,
    )


run_experiment = run_experiment_wrapper  # alias for CLI discovery
