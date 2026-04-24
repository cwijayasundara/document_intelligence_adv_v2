"""Unit tests for SQL evaluators.

Execution-match is covered by an integration test in test_sql_exec_match.py
(skipped if no DB); this file covers parse-only checks that run without a DB.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

sqlglot = pytest.importorskip("sqlglot")

from evals.evaluators import sql as sql_eval


@dataclass
class _Fake:
    outputs: dict[str, Any] = field(default_factory=dict)


def test_sql_validity_select():
    run = _Fake(outputs={"sql": "SELECT status, COUNT(*) FROM documents GROUP BY status"})
    assert sql_eval.sql_validity(run, _Fake())["score"] == 1.0


def test_sql_validity_rejects_empty():
    run = _Fake(outputs={"sql": ""})
    assert sql_eval.sql_validity(run, _Fake())["score"] == 0.0


def test_sql_safety_blocks_drop():
    run = _Fake(outputs={"sql": "DROP TABLE documents"})
    assert sql_eval.sql_safety(run, _Fake())["score"] == 0.0


def test_sql_safety_blocks_update():
    run = _Fake(outputs={"sql": "UPDATE documents SET status = 'x'"})
    assert sql_eval.sql_safety(run, _Fake())["score"] == 0.0


def test_sql_safety_allows_select():
    run = _Fake(outputs={"sql": "SELECT 1"})
    assert sql_eval.sql_safety(run, _Fake())["score"] == 1.0


def test_sql_rejected_as_expected_ok():
    run = _Fake(outputs={"sql": "", "error": "SELECT-only; cannot run DROP."})
    ex = _Fake(outputs={"expected_sql_rejected": True, "expected_error_contains": ["SELECT"]})
    assert sql_eval.sql_rejected_as_expected(run, ex)["score"] == 1.0


def test_sql_rejected_as_expected_fails_when_unsafe_sql_returned():
    run = _Fake(outputs={"sql": "DROP TABLE documents", "error": ""})
    ex = _Fake(outputs={"expected_sql_rejected": True})
    assert sql_eval.sql_rejected_as_expected(run, ex)["score"] == 0.0


def test_sql_contains_keywords_hits_all():
    run = _Fake(
        outputs={"sql": "SELECT status, COUNT(*) FROM documents GROUP BY status"}
    )
    ex = _Fake(outputs={"expected_sql_contains": ["SELECT", "COUNT", "GROUP BY"]})
    assert sql_eval.sql_contains_keywords(run, ex)["score"] == 1.0


def test_chart_shape_accepted_set():
    run = _Fake(outputs={"chart": {"chart_type": "bar"}})
    ex = _Fake(outputs={"expected_accepted_chart_types": ["pie", "bar"]})
    assert sql_eval.chart_shape(run, ex)["score"] == 1.0


def test_chart_shape_mismatch():
    run = _Fake(outputs={"chart": {"chart_type": "line"}})
    ex = _Fake(outputs={"expected_chart_type": "pie"})
    assert sql_eval.chart_shape(run, ex)["score"] == 0.0
