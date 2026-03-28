"""Tests for classifier subagent."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.classifier import ClassifierSubagent
from src.agents.schemas.classification import ClassificationResult


class TestClassifierSubagent:
    """Tests for ClassifierSubagent."""

    def setup_method(self) -> None:
        self.classifier = ClassifierSubagent()
        self.sample_categories = [
            {
                "id": uuid.uuid4(),
                "name": "LPA",
                "classification_criteria": "Limited Partnership Agreement documents",
            },
            {
                "id": uuid.uuid4(),
                "name": "Subscription Agreement",
                "classification_criteria": "Investor subscription documents",
            },
        ]
        self.sample_content = (
            "# Limited Partnership Agreement\n\n"
            "This agreement establishes Horizon Equity Partners IV..."
        )

    @pytest.mark.asyncio
    async def test_classify_returns_result(self) -> None:
        result = await self.classifier.classify(
            self.sample_content, self.sample_categories
        )
        assert isinstance(result, ClassificationResult)
        assert result.category_name in [c["name"] for c in self.sample_categories]
        assert result.reasoning

    @pytest.mark.asyncio
    async def test_classify_empty_categories(self) -> None:
        result = await self.classifier.classify(self.sample_content, [])
        assert result.category_name == "Other/Unclassified"
        assert "No categories" in result.reasoning

    @pytest.mark.asyncio
    async def test_classify_applies_pii_filter(self) -> None:
        content_with_pii = "SSN: 123-45-6789\n" + self.sample_content
        result = await self.classifier.classify(
            content_with_pii, self.sample_categories
        )
        assert isinstance(result, ClassificationResult)
        # The internal parsed content should be redacted
        assert "123-45-6789" not in self.classifier._parsed_content

    @pytest.mark.asyncio
    async def test_classify_returns_valid_category_id(self) -> None:
        result = await self.classifier.classify(
            self.sample_content, self.sample_categories
        )
        cat_ids = [c["id"] for c in self.sample_categories]
        assert result.category_id in cat_ids

    @pytest.mark.asyncio
    async def test_classify_with_mock_agent(self) -> None:
        mock_response = {
            "response": "Classified as LPA based on partnership terms."
        }
        self.classifier._agent.run = AsyncMock(return_value=mock_response)

        result = await self.classifier.classify(
            self.sample_content, self.sample_categories
        )
        assert isinstance(result, ClassificationResult)
        self.classifier._agent.run.assert_called_once()

    def test_as_subagent_slot(self) -> None:
        slot = self.classifier.as_subagent_slot()
        assert slot.name == "classifier"
        assert slot.description

    def test_build_prompt_includes_categories(self) -> None:
        prompt = self.classifier._build_prompt(
            "test content", self.sample_categories
        )
        assert "LPA" in prompt
        assert "Subscription Agreement" in prompt
        assert "test content" in prompt

    @pytest.mark.asyncio
    async def test_get_categories_tool(self) -> None:
        self.classifier._categories = self.sample_categories
        cats = await self.classifier._get_categories()
        assert cats == self.sample_categories

    @pytest.mark.asyncio
    async def test_get_parsed_content_tool(self) -> None:
        self.classifier._parsed_content = "test"
        content = await self.classifier._get_parsed_content()
        assert content == "test"
