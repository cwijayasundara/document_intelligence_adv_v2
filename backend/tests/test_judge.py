"""Tests for judge extraction function."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph_nodes.judge import (
    _assess_confidence,
    _build_prompt,
    _default_reasoning,
    judge_extraction,
)
from src.graph_nodes.schemas.extraction import (
    ExtractedField,
    FieldEvaluation,
    JudgeResult,
)


@pytest.fixture
def sample_fields() -> list[ExtractedField]:
    return [
        ExtractedField(
            field_name="fund_name",
            extracted_value="Horizon Equity Partners IV",
            source_text="...hereby establishes Horizon Equity Partners IV, a Delaware...",
        ),
        ExtractedField(
            field_name="fund_term",
            extracted_value="10 years",
            source_text="...initial term not to exceed ten years...",
        ),
    ]


@pytest.fixture
def sample_content() -> str:
    return (
        "This agreement establishes Horizon Equity Partners IV. "
        "The initial term shall not exceed ten years."
    )


class TestJudgeExtraction:
    """Tests for judge_extraction function."""

    @pytest.mark.asyncio
    async def test_returns_judge_result_on_llm_failure(
        self, sample_fields: list[ExtractedField], sample_content: str
    ) -> None:
        """When LLM call fails, heuristic fallback returns a JudgeResult."""
        with patch("src.graph_nodes.judge.get_llm", side_effect=Exception("LLM unavailable")):
            result = await judge_extraction(sample_fields, sample_content)

        assert isinstance(result, JudgeResult)
        assert len(result.evaluations) == 2

    @pytest.mark.asyncio
    async def test_field_names_match(
        self, sample_fields: list[ExtractedField], sample_content: str
    ) -> None:
        with patch("src.graph_nodes.judge.get_llm", side_effect=Exception("LLM unavailable")):
            result = await judge_extraction(sample_fields, sample_content)

        names = {e.field_name for e in result.evaluations}
        assert names == {"fund_name", "fund_term"}

    @pytest.mark.asyncio
    async def test_valid_confidence_levels(
        self, sample_fields: list[ExtractedField], sample_content: str
    ) -> None:
        with patch("src.graph_nodes.judge.get_llm", side_effect=Exception("LLM unavailable")):
            result = await judge_extraction(sample_fields, sample_content)

        valid = {"high", "medium", "low"}
        for ev in result.evaluations:
            assert ev.confidence in valid

    @pytest.mark.asyncio
    async def test_high_confidence_when_value_in_source(
        self, sample_fields: list[ExtractedField], sample_content: str
    ) -> None:
        with patch("src.graph_nodes.judge.get_llm", side_effect=Exception("LLM unavailable")):
            result = await judge_extraction(sample_fields, sample_content)

        fund_eval = next(e for e in result.evaluations if e.field_name == "fund_name")
        assert fund_eval.confidence == "high"

    @pytest.mark.asyncio
    async def test_low_confidence_when_empty(self, sample_content: str) -> None:
        fields = [
            ExtractedField(
                field_name="missing",
                extracted_value="",
                source_text="",
            ),
        ]
        with patch("src.graph_nodes.judge.get_llm", side_effect=Exception("LLM unavailable")):
            result = await judge_extraction(fields, sample_content)

        assert result.evaluations[0].confidence == "low"

    @pytest.mark.asyncio
    async def test_reasoning_provided(
        self, sample_fields: list[ExtractedField], sample_content: str
    ) -> None:
        with patch("src.graph_nodes.judge.get_llm", side_effect=Exception("LLM unavailable")):
            result = await judge_extraction(sample_fields, sample_content)

        for ev in result.evaluations:
            assert ev.reasoning
            assert len(ev.reasoning) > 0

    @pytest.mark.asyncio
    async def test_returns_llm_result_when_successful(
        self, sample_fields: list[ExtractedField], sample_content: str
    ) -> None:
        """When LLM returns a valid parsed result, it is returned directly."""
        expected = JudgeResult(
            evaluations=[
                FieldEvaluation(
                    field_name="fund_name",
                    confidence="high",
                    reasoning="Exact match.",
                ),
                FieldEvaluation(
                    field_name="fund_term",
                    confidence="medium",
                    reasoning="Inferred.",
                ),
            ]
        )

        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(return_value=expected)
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured

        with patch("src.graph_nodes.judge.get_llm", return_value=mock_llm):
            result = await judge_extraction(sample_fields, sample_content)

        assert result is expected

    @pytest.mark.asyncio
    async def test_empty_fields(self, sample_content: str) -> None:
        result = await judge_extraction([], sample_content)
        assert isinstance(result, JudgeResult)
        assert len(result.evaluations) == 0


class TestHeuristicHelpers:
    """Tests for heuristic helper functions."""

    def test_assess_confidence_high(self) -> None:
        field = ExtractedField(
            field_name="f",
            extracted_value="ABC",
            source_text="Value is ABC here",
        )
        assert _assess_confidence(field) == "high"

    def test_assess_confidence_medium_no_source(self) -> None:
        field = ExtractedField(
            field_name="f",
            extracted_value="ABC",
            source_text="",
        )
        assert _assess_confidence(field) == "medium"

    def test_assess_confidence_low_empty_value(self) -> None:
        field = ExtractedField(
            field_name="f",
            extracted_value="",
            source_text="some source",
        )
        assert _assess_confidence(field) == "low"

    def test_default_reasoning_high(self) -> None:
        field = ExtractedField(field_name="f", extracted_value="X", source_text="X")
        reasoning = _default_reasoning(field, "high")
        assert "appears in the source" in reasoning

    def test_default_reasoning_medium_no_source(self) -> None:
        field = ExtractedField(field_name="f", extracted_value="X", source_text="")
        reasoning = _default_reasoning(field, "medium")
        assert "no source quote" in reasoning

    def test_default_reasoning_low(self) -> None:
        field = ExtractedField(field_name="f", extracted_value="", source_text="")
        reasoning = _default_reasoning(field, "low")
        assert "No value" in reasoning

    def test_build_prompt_includes_fields(self) -> None:
        fields = [
            ExtractedField(
                field_name="fund_name",
                extracted_value="Test Fund",
                source_text="source",
            ),
        ]
        prompt = _build_prompt(fields, "document content")
        assert "fund_name" in prompt
        assert "document content" in prompt
