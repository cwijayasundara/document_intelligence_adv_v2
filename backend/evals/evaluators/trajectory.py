"""Trajectory evaluators for the agentic RAG — Deep Agents-style.

Grades the **sequence of tool calls** the ReAct agent made to produce an
answer, independent of whether the answer was correct. A correct answer
reached via a dozen redundant tool calls is a worse agent than one that got
there in two.

Expected `run.outputs` shape (provided by the runner — see
`backend/evals/runners/run_agentic_rag.py`):

    {
        "answer": "...",
        "trajectory": [
            {"type": "tool_call", "name": "search_documents", "args": {...}, "id": "..."},
            {"type": "tool_result", "name": "search_documents", "output": "..."},
            {"type": "tool_call", "name": "lookup_extractions", ...},
            ...
        ],
        "messages": [...],       # optional — raw LangChain messages
    }

Expected `example.outputs` (in the `rag_golden.jsonl` dataset — see
`backend/evals/datasets/rag_golden.jsonl`):

    expected_tools: ["lookup_extractions"]           # subset that MUST appear
    expected_tool_order: [["search_documents", "lookup_extractions"]]  # optional partial orders
    expected_max_calls: 3                            # penalise > max
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class HasOutputs(Protocol):
    outputs: dict[str, Any] | None


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def extract_tool_calls(messages: list[Any]) -> list[dict[str, Any]]:
    """Extract tool-call records from a LangChain message list.

    Returns the ordered list of `{"name": ..., "args": ...}` for every
    `AIMessage.tool_calls`. Tool *results* are not included (they are
    deterministic echoes of the call).
    """
    calls: list[dict[str, Any]] = []
    for msg in messages or []:
        tool_calls = getattr(msg, "tool_calls", None) or (
            msg.get("tool_calls") if isinstance(msg, dict) else None
        )
        if not tool_calls:
            continue
        for tc in tool_calls:
            name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
            args = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", {})
            if name:
                calls.append({"name": name, "args": args or {}})
    return calls


def _trajectory_calls(run: HasOutputs) -> list[dict[str, Any]]:
    """Accept either `trajectory` (preferred) or raw `messages`."""
    traj = _get(run.outputs, "trajectory")
    if traj:
        return [
            {"name": _get(entry, "name"), "args": _get(entry, "args") or {}}
            for entry in traj
            if _get(entry, "type") == "tool_call"
            or (isinstance(entry, dict) and "name" in entry and "args" in entry)
        ]
    return extract_tool_calls(_get(run.outputs, "messages") or [])


# --- Evaluators


def trajectory_subset(run: HasOutputs, example: HasOutputs) -> dict[str, Any]:
    """Required tools ⊆ actually-called tools (at least once)."""
    required = (example.outputs or {}).get("expected_tools") or []
    if not required:
        return {"key": "trajectory_subset", "score": None, "comment": "no expected_tools"}
    actual = {c["name"] for c in _trajectory_calls(run) if c["name"]}
    missing = [t for t in required if t not in actual]
    score = 1.0 if not missing else (len(required) - len(missing)) / len(required)
    return {
        "key": "trajectory_subset",
        "score": round(score, 3),
        "comment": f"missing={missing} required={required} actual={sorted(actual)}",
    }


def trajectory_order(run: HasOutputs, example: HasOutputs) -> dict[str, Any]:
    """Each expected partial-order pair `[before, after]` must be respected.

    `expected_tool_order`: list of 2-lists — each pair `[A, B]` asserts "a
    call to A must precede a call to B when both appear".
    """
    pairs = (example.outputs or {}).get("expected_tool_order") or []
    if not pairs:
        return {"key": "trajectory_order", "score": None, "comment": "no order constraints"}

    calls = _trajectory_calls(run)
    names = [c["name"] for c in calls if c["name"]]
    violated: list[str] = []
    for pair in pairs:
        if len(pair) != 2:
            continue
        before, after = pair
        try:
            idx_before = names.index(before)
        except ValueError:
            violated.append(f"{before} never called")
            continue
        try:
            idx_after = names.index(after, idx_before + 1)  # after must come later
            _ = idx_after
        except ValueError:
            violated.append(f"{after} did not follow {before}")

    score = 1.0 if not violated else max(0.0, 1.0 - len(violated) / len(pairs))
    return {
        "key": "trajectory_order",
        "score": round(score, 3),
        "comment": f"violated={violated} actual={names}",
    }


def no_unnecessary_calls(run: HasOutputs, example: HasOutputs) -> dict[str, Any]:
    """Score drops linearly with calls beyond `expected_max_calls`.

    score = 1.0 when #calls ≤ max; 0.5 at 2x; 0.0 at 3x or more.
    """
    max_calls = (example.outputs or {}).get("expected_max_calls")
    calls = _trajectory_calls(run)
    n = len(calls)
    if max_calls is None:
        return {"key": "no_unnecessary_calls", "score": None, "comment": f"n={n}"}
    max_calls = int(max_calls)
    if n <= max_calls:
        return {"key": "no_unnecessary_calls", "score": 1.0, "comment": f"n={n} max={max_calls}"}
    excess = n - max_calls
    penalty = min(1.0, excess / max(1, max_calls))
    score = max(0.0, 1.0 - penalty)
    return {
        "key": "no_unnecessary_calls",
        "score": round(score, 3),
        "comment": f"n={n} max={max_calls} excess={excess}",
    }


async def tool_input_quality(run: HasOutputs, example: HasOutputs) -> dict[str, Any]:
    """LLM-judge grades whether tool-call arguments improved over the user query.

    For `search_documents`, a good reformulation is more specific than the
    original question. For `lookup_extractions`, the doc_id/field_name should
    match the intended entity. This is a soft signal; 0 → n/a when no
    tool calls present.
    """
    query = _get(example, "inputs", {}).get("query") or ""
    calls = _trajectory_calls(run)
    if not query or not calls:
        return {"key": "tool_input_quality", "score": None, "comment": "nothing to judge"}

    from evals.evaluators.llm_judge._base import BinaryJudgement, structured_call

    system = (
        "You grade whether an agent's TOOL_CALL_ARGS are a better query than the"
        " original USER_QUERY. Reformulation = more specific keywords, clearer"
        " intent, correct entity references. Return passed (bool), score [0,1],"
        " and a one-sentence reasoning."
    )
    user = f"USER_QUERY: {query}\n\n" + "\n".join(
        f"TOOL_CALL[{i}]: {c['name']}({c['args']})" for i, c in enumerate(calls)
    )
    judged: BinaryJudgement = await structured_call(system, user, BinaryJudgement)  # type: ignore[assignment]
    return {
        "key": "tool_input_quality",
        "score": round(judged.score, 3),
        "comment": f"passed={judged.passed} — {judged.reasoning}",
    }


ALL_EVALUATORS = {
    "trajectory_subset": trajectory_subset,
    "trajectory_order": trajectory_order,
    "no_unnecessary_calls": no_unnecessary_calls,
    "tool_input_quality": tool_input_quality,
}
