"""Tests for extractor subagent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.extractor import build_dynamic_model
from src.agents.schemas.extraction import ExtractionResult


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


class TestExtractorSubagent:
    """Tests for ExtractorSubagent."""

    def setup_method(self) -> None:
        with patch("src.agents.extractor.create_deep_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(
                return_value={
                    "structured_response": None,
                    "response": "Extracted values",
                }
            )
            mock_create.return_value = mock_agent
            from src.agents.extractor import ExtractorSubagent

            self.extractor = ExtractorSubagent()

        self.sample_fields = [
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
        self.sample_content = (
            "# LPA Document\n\n"
            "Fund Name: Horizon Equity Partners IV\n"
            "Management Fee: 2.0% per annum"
        )

    @pytest.mark.asyncio
    async def test_extract_returns_result(self) -> None:
        with patch("src.agents.extractor.create_deep_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(
                return_value={
                    "structured_response": None,
                    "response": "Extracted",
                }
            )
            mock_create.return_value = mock_agent
            result = await self.extractor.extract(self.sample_content, self.sample_fields)
        assert isinstance(result, ExtractionResult)
        assert len(result.fields) == 2

    @pytest.mark.asyncio
    async def test_extract_field_names_match(self) -> None:
        with patch("src.agents.extractor.create_deep_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(
                return_value={
                    "structured_response": None,
                    "response": "Extracted",
                }
            )
            mock_create.return_value = mock_agent
            result = await self.extractor.extract(self.sample_content, self.sample_fields)
        field_names = {f.field_name for f in result.fields}
        expected = {"fund_name", "management_fee"}
        assert field_names == expected

    @pytest.mark.asyncio
    async def test_extract_applies_pii_filter(self) -> None:
        with patch("src.agents.extractor.create_deep_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(
                return_value={
                    "structured_response": None,
                    "response": "Extracted",
                }
            )
            mock_create.return_value = mock_agent
            content = "SSN: 123-45-6789\n" + self.sample_content
            await self.extractor.extract(content, self.sample_fields)
        assert "123-45-6789" not in self.extractor._parsed_content

    @pytest.mark.asyncio
    async def test_extract_empty_fields(self) -> None:
        result = await self.extractor.extract(self.sample_content, [])
        assert isinstance(result, ExtractionResult)
        assert len(result.fields) == 0

    def test_as_subagent_config(self) -> None:
        config = self.extractor.as_subagent_config()
        assert config["name"] == "extractor"
        assert config["description"]

    @pytest.mark.asyncio
    async def test_get_extraction_schema_tool(self) -> None:
        self.extractor._schema_fields = self.sample_fields
        schema = await self.extractor._get_extraction_schema()
        assert schema == self.sample_fields

    @pytest.mark.asyncio
    async def test_get_parsed_content_tool(self) -> None:
        self.extractor._parsed_content = "test content"
        content = await self.extractor._get_parsed_content()
        assert content == "test content"

    def test_build_prompt_includes_fields(self) -> None:
        prompt = self.extractor._build_prompt("test content", self.sample_fields)
        assert "fund_name" in prompt
        assert "management_fee" in prompt
