"""Unit tests for trajectory evaluators.

LLM-based `tool_input_quality` is not exercised here — those are covered in
LLM-using integration tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from evals.evaluators import trajectory as traj


@dataclass
class _Fake:
    outputs: dict[str, Any] = field(default_factory=dict)
    inputs: dict[str, Any] = field(default_factory=dict)


def _tc(name: str, **args: Any) -> dict[str, Any]:
    return {"type": "tool_call", "name": name, "args": args}


# --- subset


def test_subset_all_required_called():
    run = _Fake(outputs={"trajectory": [_tc("search_documents"), _tc("lookup_extractions")]})
    ex = _Fake(outputs={"expected_tools": ["search_documents", "lookup_extractions"]})
    assert traj.trajectory_subset(run, ex)["score"] == 1.0


def test_subset_partial():
    run = _Fake(outputs={"trajectory": [_tc("search_documents")]})
    ex = _Fake(outputs={"expected_tools": ["search_documents", "lookup_extractions"]})
    assert traj.trajectory_subset(run, ex)["score"] == 0.5


# --- order


def test_order_respected():
    run = _Fake(outputs={"trajectory": [_tc("search_documents"), _tc("lookup_extractions")]})
    ex = _Fake(outputs={"expected_tool_order": [["search_documents", "lookup_extractions"]]})
    assert traj.trajectory_order(run, ex)["score"] == 1.0


def test_order_violated():
    run = _Fake(outputs={"trajectory": [_tc("lookup_extractions"), _tc("search_documents")]})
    ex = _Fake(outputs={"expected_tool_order": [["search_documents", "lookup_extractions"]]})
    assert traj.trajectory_order(run, ex)["score"] == 0.0


def test_order_partial():
    run = _Fake(
        outputs={
            "trajectory": [
                _tc("search_documents"),
                _tc("lookup_extractions"),
                _tc("get_document_summary"),  # but should precede extraction
            ]
        }
    )
    ex = _Fake(
        outputs={
            "expected_tool_order": [
                ["search_documents", "lookup_extractions"],
                ["get_document_summary", "lookup_extractions"],  # violated
            ]
        }
    )
    result = traj.trajectory_order(run, ex)
    assert result["score"] == 0.5


# --- no_unnecessary_calls


def test_no_unnecessary_within_budget():
    run = _Fake(outputs={"trajectory": [_tc("search_documents")]})
    ex = _Fake(outputs={"expected_max_calls": 2})
    assert traj.no_unnecessary_calls(run, ex)["score"] == 1.0


def test_no_unnecessary_excess():
    run = _Fake(outputs={"trajectory": [_tc("x"), _tc("x"), _tc("x"), _tc("x")]})
    ex = _Fake(outputs={"expected_max_calls": 2})
    result = traj.no_unnecessary_calls(run, ex)
    # n=4, max=2, excess=2, penalty = min(1, 2/2)=1 → score=0
    assert result["score"] == 0.0


def test_no_unnecessary_modest_excess():
    run = _Fake(outputs={"trajectory": [_tc("x"), _tc("x"), _tc("x")]})
    ex = _Fake(outputs={"expected_max_calls": 2})
    result = traj.no_unnecessary_calls(run, ex)
    # n=3, max=2, excess=1, penalty=0.5 → score=0.5
    assert result["score"] == 0.5


# --- extract_tool_calls from message list (LangChain shape)


def test_extract_tool_calls_from_messages():
    class _AIMsg:
        tool_calls = [{"name": "search_documents", "args": {"query": "fee"}}]

    class _UserMsg:
        pass

    messages = [_UserMsg(), _AIMsg(), _UserMsg()]
    calls = traj.extract_tool_calls(messages)
    assert calls == [{"name": "search_documents", "args": {"query": "fee"}}]
