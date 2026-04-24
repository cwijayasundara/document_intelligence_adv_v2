"""Unit tests for the rubric aggregation logic — no LLM needed."""

from __future__ import annotations

import pytest
from evals.evaluators.rubric import (
    CriterionScore,
    Rubric,
    RubricVerdict,
    _aggregate,
    load_rubric,
)


@pytest.fixture
def rubric_four_crit() -> Rubric:
    return Rubric(
        name="extraction",
        description="test",
        scale=(1, 5),
        criteria=[
            {"id": "a", "weight": 0.4},
            {"id": "b", "weight": 0.3},
            {"id": "c", "weight": 0.2},
            {"id": "d", "weight": 0.1},
        ],
    )


def test_aggregate_all_top(rubric_four_crit: Rubric) -> None:
    verdict = RubricVerdict(
        scores=[
            CriterionScore(id="a", score=5, reasoning="."),
            CriterionScore(id="b", score=5, reasoning="."),
            CriterionScore(id="c", score=5, reasoning="."),
            CriterionScore(id="d", score=5, reasoning="."),
        ]
    )
    result = _aggregate(rubric_four_crit, verdict)
    assert result["score"] == 1.0
    assert result["raw_score"] == 5.0


def test_aggregate_all_bottom(rubric_four_crit: Rubric) -> None:
    verdict = RubricVerdict(scores=[CriterionScore(id=c, score=1, reasoning=".") for c in "abcd"])
    result = _aggregate(rubric_four_crit, verdict)
    assert result["score"] == 0.0
    assert result["raw_score"] == 1.0


def test_aggregate_weighted_mix(rubric_four_crit: Rubric) -> None:
    # a=5 (w0.4), b=1 (w0.3), c=3 (w0.2), d=5 (w0.1)
    # raw = 0.4*5 + 0.3*1 + 0.2*3 + 0.1*5 = 2+0.3+0.6+0.5 = 3.4
    # normalised = (5-1)/(5-1)=1; (1-1)/4=0; (3-1)/4=0.5; (5-1)/4=1
    # weighted norm = 0.4*1 + 0.3*0 + 0.2*0.5 + 0.1*1 = 0.4+0+0.1+0.1 = 0.6
    verdict = RubricVerdict(
        scores=[
            CriterionScore(id="a", score=5, reasoning="."),
            CriterionScore(id="b", score=1, reasoning="."),
            CriterionScore(id="c", score=3, reasoning="."),
            CriterionScore(id="d", score=5, reasoning="."),
        ]
    )
    result = _aggregate(rubric_four_crit, verdict)
    assert result["raw_score"] == pytest.approx(3.4, abs=1e-6)
    assert result["score"] == pytest.approx(0.6, abs=1e-6)


def test_aggregate_missing_criterion_defaults_to_floor(rubric_four_crit: Rubric) -> None:
    # 'c' missing — treated as floor (score=1 in a 1..5 rubric).
    verdict = RubricVerdict(
        scores=[
            CriterionScore(id="a", score=5, reasoning="."),
            CriterionScore(id="b", score=5, reasoning="."),
            CriterionScore(id="d", score=5, reasoning="."),
        ]
    )
    result = _aggregate(rubric_four_crit, verdict)
    assert result["criteria"]["c"]["score"] == 1.0
    assert "missing" in result["criteria"]["c"]["reasoning"]


def test_aggregate_clips_out_of_range(rubric_four_crit: Rubric) -> None:
    verdict = RubricVerdict(
        scores=[
            CriterionScore(id="a", score=99, reasoning="."),  # clipped to 5
            CriterionScore(id="b", score=-5, reasoning="."),  # clipped to 1
            CriterionScore(id="c", score=3, reasoning="."),
            CriterionScore(id="d", score=3, reasoning="."),
        ]
    )
    result = _aggregate(rubric_four_crit, verdict)
    assert result["criteria"]["a"]["score"] == 5.0
    assert result["criteria"]["b"]["score"] == 1.0


def test_load_rubric_existing_file() -> None:
    r = load_rubric("extraction")
    assert r.name == "extraction"
    assert r.scale == (1, 5)
    assert any(c["id"] == "verbatim_quote" for c in r.criteria)


def test_load_rubric_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        load_rubric("nope_not_a_rubric")
