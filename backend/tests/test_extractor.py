"""Tests for extractor function."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph_nodes.extractor import _build_prompt, build_dynamic_model, extract_fields
from src.graph_nodes.schemas.extraction import ExtractionResult


class TestBuildDynamicModel:
    """Tests for build_dynamic_model."""

    def test_builds_model_with_string_fields(self) -> None:
        fields = [
            {"field_name": "fund_name", "data_type": "string", "description": "Fund name"},
            {"field_name": "fund_term", "data_type": "string", "description": "Fund term"},
        ]
        model = build_dynamic_model(fields)
        instance = model(fund_name="Test Fund", fund_term="10 years")
        assert instance.fund_name == "Test Fund"

    def test_builds_model_with_number_fields(self) -> None:
        fields = [
            {"field_name": "fee_rate", "data_type": "number", "description": "Fee rate"},
        ]
        model = build_dynamic_model(fields)
        instance = model(fee_rate=2.0)
        assert instance.fee_rate == 2.0

    def test_builds_model_with_optional_fields(self) -> None:
        fields = [
            {"field_name": "fund_name", "data_type": "string", "description": ""},
        ]
        model = build_dynamic_model(fields)
        instance = model()
        assert instance.fund_name is None

    def test_builds_model_unknown_type_defaults_to_string(self) -> None:
        fields = [
            {"field_name": "custom", "data_type": "unknown_type", "description": ""},
        ]
        model = build_dynamic_model(fields)
        instance = model(custom="test")
        assert instance.custom == "test"

    def test_builds_model_empty_fields(self) -> None:
        model = build_dynamic_model([])
        instance = model()
        assert instance is not None


class TestExtractFields:
    """Tests for extract_fields()."""

    sample_fields = [
        {
            "field_name": "fund_name",
            "display_name": "Fund Name",
            "data_type": "string",
            "description": "Name of the fund",
        },
        {
            "field_name": "management_fee",
            "display_name": "Management Fee",
            "data_type": "percentage",
            "description": "Annual management fee rate",
        },
    ]
    sample_content = (
        "# LPA Document\n\n"
        "Fund Name: Horizon Equity Partners IV\n"
        "Management Fee: 2.0% per annum"
    )

    def _mk_llm(self, structured_result) -> MagicMock:
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(return_value=structured_result)
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured
        return mock_llm

    @pytest.mark.asyncio
    async def test_extract_returns_result(self) -> None:
        # Build a dummy structured output object whose attributes match expected fields
        structured = MagicMock()
        structured.fund_name = "Horizon Equity Partners IV"
        structured.fund_name_source = "Fund Name: Horizon Equity Partners IV"
        structured.management_fee = "2.0%"
        structured.management_fee_source = "Management Fee: 2.0% per annum"

        mock_llm = self._mk_llm(structured)
        with patch("src.graph_nodes.extractor.get_llm", return_value=mock_llm):
            result = await extract_fields(self.sample_content, self.sample_fields)
        assert isinstance(result, ExtractionResult)
        assert len(result.fields) == 2

    @pytest.mark.asyncio
    async def test_extract_field_names_match(self) -> None:
        structured = MagicMock()
        structured.fund_name = "Horizon Equity Partners IV"
        structured.fund_name_source = "source"
        structured.management_fee = "2.0%"
        structured.management_fee_source = "source"

        mock_llm = self._mk_llm(structured)
        with patch("src.graph_nodes.extractor.get_llm", return_value=mock_llm):
            result = await extract_fields(self.sample_content, self.sample_fields)
        field_names = {f.field_name for f in result.fields}
        expected = {"fund_name", "management_fee"}
        assert field_names == expected

    @pytest.mark.asyncio
    async def test_extract_applies_pii_filter(self) -> None:
        structured = MagicMock()
        structured.fund_name = "Horizon"
        structured.fund_name_source = "s"
        structured.management_fee = "2%"
        structured.management_fee_source = "s"

        mock_llm = self._mk_llm(structured)
        with patch("src.graph_nodes.extractor.get_llm", return_value=mock_llm):
            content = "SSN: 123-45-6789\n" + self.sample_content
            await extract_fields(content, self.sample_fields)

        # Inspect the prompt sent to the LLM — SSN should have been redacted
        call_args = mock_llm.with_structured_output.return_value.ainvoke.call_args
        messages = call_args[0][0]
        prompt_text = messages[-1].content
        assert "123-45-6789" not in prompt_text

    @pytest.mark.asyncio
    async def test_extract_empty_fields(self) -> None:
        result = await extract_fields(self.sample_content, [])
        assert isinstance(result, ExtractionResult)
        assert len(result.fields) == 0

    def test_build_prompt_includes_fields(self) -> None:
        prompt = _build_prompt("test content", self.sample_fields)
        assert "fund_name" in prompt
        assert "management_fee" in prompt
