"""Tests for judge subagent."""

from unittest.mock import AsyncMock

import pytest

from src.agents.judge import JudgeSubagent
from src.agents.schemas.extraction import ExtractedField, JudgeResult


class TestJudgeSubagent:
    """Tests for JudgeSubagent."""

    def setup_method(self) -> None:
        self.judge = JudgeSubagent()
        self.sample_fields = [
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
        self.sample_content = (
            "This agreement establishes Horizon Equity Partners IV. "
            "The initial term shall not exceed ten years."
        )

    @pytest.mark.asyncio
    async def test_evaluate_returns_judge_result(self) -> None:
        result = await self.judge.evaluate(
            self.sample_fields, self.sample_content
        )
        assert isinstance(result, JudgeResult)
        assert len(result.evaluations) == 2

    @pytest.mark.asyncio
    async def test_evaluate_field_names_match(self) -> None:
        result = await self.judge.evaluate(
            self.sample_fields, self.sample_content
        )
        names = {e.field_name for e in result.evaluations}
        assert names == {"fund_name", "fund_term"}

    @pytest.mark.asyncio
    async def test_evaluate_valid_confidence_levels(self) -> None:
        result = await self.judge.evaluate(
            self.sample_fields, self.sample_content
        )
        valid = {"high", "medium", "low"}
        for ev in result.evaluations:
            assert ev.confidence in valid

    @pytest.mark.asyncio
    async def test_evaluate_high_confidence_when_value_in_source(self) -> None:
        result = await self.judge.evaluate(
            self.sample_fields, self.sample_content
        )
        fund_eval = next(
            e for e in result.evaluations if e.field_name == "fund_name"
        )
        assert fund_eval.confidence == "high"

    @pytest.mark.asyncio
    async def test_evaluate_low_confidence_when_empty(self) -> None:
        fields = [
            ExtractedField(
                field_name="missing",
                extracted_value="",
                source_text="",
            ),
        ]
        result = await self.judge.evaluate(fields, self.sample_content)
        assert result.evaluations[0].confidence == "low"

    @pytest.mark.asyncio
    async def test_evaluate_applies_pii_filter(self) -> None:
        content = "SSN: 123-45-6789\n" + self.sample_content
        await self.judge.evaluate(self.sample_fields, content)
        assert "123-45-6789" not in self.judge._parsed_content

    @pytest.mark.asyncio
    async def test_evaluate_reasoning_provided(self) -> None:
        result = await self.judge.evaluate(
            self.sample_fields, self.sample_content
        )
        for ev in result.evaluations:
            assert ev.reasoning
            assert len(ev.reasoning) > 0

    @pytest.mark.asyncio
    async def test_evaluate_with_mock_agent(self) -> None:
        self.judge._agent.run = AsyncMock(
            return_value={"response": "Evaluated"}
        )
        result = await self.judge.evaluate(
            self.sample_fields, self.sample_content
        )
        assert isinstance(result, JudgeResult)
        self.judge._agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_empty_fields(self) -> None:
        result = await self.judge.evaluate([], self.sample_content)
        assert isinstance(result, JudgeResult)
        assert len(result.evaluations) == 0

    def test_as_subagent_slot(self) -> None:
        slot = self.judge.as_subagent_slot()
        assert slot.name == "judge"
        assert slot.description

    @pytest.mark.asyncio
    async def test_get_extracted_values_tool(self) -> None:
        self.judge._extracted_fields = self.sample_fields
        values = await self.judge._get_extracted_values()
        assert len(values) == 2
        assert values[0]["field_name"] == "fund_name"

    @pytest.mark.asyncio
    async def test_get_parsed_content_tool(self) -> None:
        self.judge._parsed_content = "test content"
        content = await self.judge._get_parsed_content()
        assert content == "test content"

    def test_build_prompt_includes_fields(self) -> None:
        prompt = self.judge._build_prompt(
            self.sample_fields, "document content"
        )
        assert "fund_name" in prompt
        assert "fund_term" in prompt
        assert "document content" in prompt
