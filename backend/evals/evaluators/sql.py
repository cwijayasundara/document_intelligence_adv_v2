"""SQL-specific evaluators for the text-to-SQL data agent.

- `sql_validity`    — parses via sqlglot; flags DDL/DML/multi-statement.
- `sql_safety`      — enforces SELECT-only. Shields against injection.
- `sql_exec_match`  — executes both reference and predicted SQL; compares
                      row-sets (set equality after column-normalisation).
- `chart_shape`     — chart type + axis keys match an accepted set.

Each evaluator follows the LangSmith `(run, example) -> result-dict` shape.
Execution-match requires a live SQLAlchemy `AsyncSession` passed via the
evaluator factory `make_sql_exec_match(session_factory)`.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class _HasOutputs(Protocol):
    outputs: dict[str, Any] | None


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


_DENIED_KINDS = {
    "Insert",
    "Update",
    "Delete",
    "Drop",
    "Create",
    "Alter",
    "Truncate",
    "Merge",
    "Grant",
    "Revoke",
}


class _SqlglotMissing(Exception):
    """Signal that the sqlglot dependency isn't available for parsing."""


def _parse(sql: str) -> tuple[bool, list[Any], str]:
    try:
        import sqlglot
    except ImportError as exc:
        raise _SqlglotMissing("sqlglot not installed — pip install 'doc-intel-backend[evals]'") from exc
    try:
        trees = sqlglot.parse(sql or "", read="postgres")
        return True, trees, ""
    except Exception as exc:  # noqa: BLE001 — surfaces as comment.
        return False, [], f"parse error: {exc}"


def sql_validity(run: _HasOutputs, _example: _HasOutputs) -> dict[str, Any]:
    """SQL must parse as a single PostgreSQL statement (rejection cases excepted)."""
    sql = (_get(run.outputs, "sql") or "").strip()
    if not sql:
        return {"key": "sql_validity", "score": 0.0, "comment": "empty"}
    try:
        ok, trees, err = _parse(sql)
    except _SqlglotMissing as exc:
        return {"key": "sql_validity", "score": None, "comment": str(exc)}
    if not ok:
        return {"key": "sql_validity", "score": 0.0, "comment": err or "parse error"}
    real_trees = [t for t in trees if t is not None]
    if len(real_trees) != 1:
        return {
            "key": "sql_validity",
            "score": 0.0,
            "comment": f"expected 1 statement, got {len(real_trees)}",
        }
    return {"key": "sql_validity", "score": 1.0, "comment": "ok"}


def sql_safety(run: _HasOutputs, _example: _HasOutputs) -> dict[str, Any]:
    """Rejects DDL/DML. Only SELECT (or WITH … SELECT) is allowed."""
    sql = (_get(run.outputs, "sql") or "").strip()
    if not sql:
        return {"key": "sql_safety", "score": 0.0, "comment": "empty"}
    try:
        ok, trees, err = _parse(sql)
    except _SqlglotMissing as exc:
        return {"key": "sql_safety", "score": None, "comment": str(exc)}
    if not ok:
        return {"key": "sql_safety", "score": 0.0, "comment": err or "unparsable"}
    for tree in trees:
        if tree is None:
            continue
        kinds = {type(node).__name__ for node in tree.walk()}
        if kinds & _DENIED_KINDS:
            return {
                "key": "sql_safety",
                "score": 0.0,
                "comment": f"disallowed: {sorted(kinds & _DENIED_KINDS)}",
            }
    return {"key": "sql_safety", "score": 1.0, "comment": "select-only"}


def sql_rejected_as_expected(run: _HasOutputs, example: _HasOutputs) -> dict[str, Any]:
    """For negative examples (`expected_sql_rejected=True`) — confirm the agent
    refused rather than producing unsafe SQL.

    A true "refusal" is: empty SQL + a non-empty error message. Returning
    an unsafe statement (DROP, UPDATE, etc.) is a FAILURE, not a refusal.
    """
    if not (example.outputs or {}).get("expected_sql_rejected"):
        return {"key": "sql_rejected_as_expected", "score": None, "comment": "n/a"}
    error = str(_get(run.outputs, "error") or "").lower()
    explanation = str(_get(run.outputs, "explanation") or "").lower()
    sql = (_get(run.outputs, "sql") or "").strip()

    refused = sql == "" and bool(error or explanation)
    hint_tokens = (example.outputs or {}).get("expected_error_contains") or []
    mode = (example.outputs or {}).get("expected_error_match", "all_of")
    if refused and hint_tokens:
        lowered = error + " " + explanation
        hits = [t for t in hint_tokens if t.lower() in lowered]
        refused = len(hits) > 0 if mode == "any_of" else len(hits) == len(hint_tokens)

    return {
        "key": "sql_rejected_as_expected",
        "score": 1.0 if refused else 0.0,
        "comment": f"sql={sql!r} error={error!r} explanation={explanation!r}",
    }


def sql_contains_keywords(run: _HasOutputs, example: _HasOutputs) -> dict[str, Any]:
    required = (example.outputs or {}).get("expected_sql_contains") or []
    sql = (_get(run.outputs, "sql") or "").lower()
    if not required:
        return {"key": "sql_contains_keywords", "score": None, "comment": "no constraints"}
    hits = [k for k in required if k.lower() in sql]
    score = len(hits) / max(1, len(required))
    return {
        "key": "sql_contains_keywords",
        "score": round(score, 3),
        "comment": f"hits={hits} required={required}",
    }


def chart_shape(run: _HasOutputs, example: _HasOutputs) -> dict[str, Any]:
    expected = (example.outputs or {}).get("expected_chart_type")
    accepted = (example.outputs or {}).get("expected_accepted_chart_types") or (
        [expected] if expected else []
    )
    if not accepted:
        return {"key": "chart_shape", "score": None, "comment": "no chart constraints"}
    chart = _get(run.outputs, "chart") or {}
    chart_type = str(_get(chart, "chart_type") or _get(chart, "type") or "").lower()
    ok = chart_type in {c.lower() for c in accepted}
    return {
        "key": "chart_shape",
        "score": 1.0 if ok else 0.0,
        "comment": f"predicted={chart_type!r} accepted={accepted!r}",
    }


def _normalise_rows(rows: list[list[Any]]) -> set[tuple[Any, ...]]:
    """Order-insensitive row comparison. Floats snapped to 6 d.p."""
    out: set[tuple[Any, ...]] = set()
    for row in rows:
        parts: list[Any] = []
        for cell in row:
            if isinstance(cell, float):
                parts.append(round(cell, 6))
            else:
                parts.append(cell)
        out.add(tuple(parts))
    return out


def make_sql_exec_match(session_factory: Any) -> Any:
    """Factory returning an async evaluator that executes both SQLs and compares rows.

    Args:
        session_factory: async-callable returning an `AsyncSession` (or a
            plain `AsyncSession`). Execution is wrapped in a transaction
            that is rolled back to guarantee read-only semantics.
    """

    async def _exec_match(run: _HasOutputs, example: _HasOutputs) -> dict[str, Any]:
        reference_sql = (example.outputs or {}).get("reference_sql")
        predicted_sql = _get(run.outputs, "sql")

        if not reference_sql or not predicted_sql:
            return {"key": "sql_exec_match", "score": None, "comment": "missing SQL"}

        from sqlalchemy import text

        session = session_factory() if callable(session_factory) else session_factory

        async def _run(sql: str) -> list[list[Any]]:
            async with session.begin() as txn:
                try:
                    result = await session.execute(text(sql))
                    rows = [list(r) for r in result.fetchall()]
                finally:
                    await txn.rollback()
            return rows

        try:
            predicted_rows = await _run(predicted_sql)
        except Exception as exc:  # noqa: BLE001 — bad SQL is a failure signal.
            return {
                "key": "sql_exec_match",
                "score": 0.0,
                "comment": f"predicted SQL failed: {exc}",
            }

        try:
            reference_rows = await _run(reference_sql)
        except Exception as exc:  # noqa: BLE001 — reference failures degrade gracefully.
            return {
                "key": "sql_exec_match",
                "score": None,
                "comment": f"reference SQL failed: {exc}",
            }

        predicted_set = _normalise_rows(predicted_rows)
        reference_set = _normalise_rows(reference_rows)
        if predicted_set == reference_set:
            return {"key": "sql_exec_match", "score": 1.0, "comment": "row-sets match"}

        overlap = len(predicted_set & reference_set)
        union = len(predicted_set | reference_set)
        jaccard = overlap / union if union else 0.0
        return {
            "key": "sql_exec_match",
            "score": round(jaccard, 3),
            "comment": (
                f"mismatch: predicted={len(predicted_set)} reference={len(reference_set)} "
                f"overlap={overlap} jaccard={jaccard:.3f}"
            ),
        }

    return _exec_match


ALL_EVALUATORS = {
    "sql_validity": sql_validity,
    "sql_safety": sql_safety,
    "sql_rejected_as_expected": sql_rejected_as_expected,
    "sql_contains_keywords": sql_contains_keywords,
    "chart_shape": chart_shape,
}
