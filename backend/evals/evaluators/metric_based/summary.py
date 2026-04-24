"""Summary metrics — PE-checklist coverage + topic count."""

from __future__ import annotations

from typing import Any

from ._helpers import HasOutputs, get, norm_loose


def summary_pe_checklist_coverage(run: HasOutputs, example: HasOutputs) -> dict[str, Any]:
    """Fraction of PE-checklist items that appear (case-insensitively) in the summary."""
    checklist = (example.outputs or {}).get("pe_checklist") or {}
    if not checklist:
        return {"key": "summary_pe_checklist_coverage", "score": None, "comment": "no checklist"}
    summary = norm_loose(get(run.outputs, "summary") or "")
    present = [k for k, v in checklist.items() if v and norm_loose(v) in summary]
    score = len(present) / max(1, len(checklist))
    return {
        "key": "summary_pe_checklist_coverage",
        "score": round(score, 3),
        "comment": f"present={present} missing={sorted(set(checklist) - set(present))}",
    }


def summary_topic_count(run: HasOutputs, example: HasOutputs) -> dict[str, Any]:
    expected_min = (example.outputs or {}).get("expected_min_topics")
    topics = get(run.outputs, "key_topics") or []
    if expected_min is None:
        return {"key": "summary_topic_count", "score": None, "comment": "no min"}
    ok = len(topics) >= int(expected_min)
    return {
        "key": "summary_topic_count",
        "score": 1.0 if ok else 0.0,
        "comment": f"topics={len(topics)} min={expected_min}",
    }
