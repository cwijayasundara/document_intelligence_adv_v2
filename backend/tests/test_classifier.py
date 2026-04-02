"""Tests for classifier subagent."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.schemas.classification import ClassificationResult


class TestClassifierSubagent:
    """Tests for ClassifierSubagent."""

    def setup_method(self) -> None:
        # Patch create_deep_agent so ClassifierSubagent.__init__ doesn't call real SDK
        with patch("src.agents.classifier.create_deep_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(
                return_value={
                    "structured_response": None,
                    "response": "Classified as LPA based on partnership terms.",
                    "messages": [],
                }
            )
            mock_create.return_value = mock_agent
            from src.agents.classifier import ClassifierSubagent

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
            file_name="LPA_Fund.pdf",
            content=self.sample_content,
            categories=self.sample_categories,
        )
        assert isinstance(result, ClassificationResult)
        assert result.category_name in [c["name"] for c in self.sample_categories]
        assert result.reasoning
        assert 0 <= result.confidence <= 100

    @pytest.mark.asyncio
    async def test_classify_empty_categories(self) -> None:
        result = await self.classifier.classify(
            file_name="doc.pdf",
            content=self.sample_content,
            categories=[],
        )
        assert result.category_name == "Other/Unclassified"
        assert "No categories" in result.reasoning
        assert result.confidence == 0

    @pytest.mark.asyncio
    async def test_classify_with_summary(self) -> None:
        """When summary is provided, it is used for classification."""
        result = await self.classifier.classify(
            file_name="LPA_Fund.pdf",
            content=self.sample_content,
            categories=self.sample_categories,
            summary="This is a Limited Partnership Agreement for Horizon Fund.",
        )
        assert isinstance(result, ClassificationResult)
        # Verify the prompt included the summary
        call_args = self.classifier._agent.ainvoke.call_args
        prompt = call_args[0][0]["messages"][0]["content"]
        assert "Document summary" in prompt

    @pytest.mark.asyncio
    async def test_classify_without_summary_uses_content(self) -> None:
        """When no summary, full content is used."""
        result = await self.classifier.classify(
            file_name="doc.pdf",
            content=self.sample_content,
            categories=self.sample_categories,
        )
        assert isinstance(result, ClassificationResult)
        call_args = self.classifier._agent.ainvoke.call_args
        prompt = call_args[0][0]["messages"][0]["content"]
        assert "Document content" in prompt

    @pytest.mark.asyncio
    async def test_classify_returns_valid_category_id(self) -> None:
        result = await self.classifier.classify(
            file_name="doc.pdf",
            content=self.sample_content,
            categories=self.sample_categories,
        )
        cat_ids = [c["id"] for c in self.sample_categories]
        assert result.category_id in cat_ids

    @pytest.mark.asyncio
    async def test_classify_with_structured_response(self) -> None:
        """When structured_response is a ClassificationResult, it is returned directly."""
        expected = ClassificationResult(
            category_id=self.sample_categories[0]["id"],
            category_name="LPA",
            confidence=95,
            reasoning="Matched based on partnership language.",
        )
        self.classifier._agent.ainvoke = AsyncMock(
            return_value={
                "structured_response": expected,
                "response": "",
                "messages": [],
            }
        )

        result = await self.classifier.classify(
            file_name="LPA_Fund.pdf",
            content=self.sample_content,
            categories=self.sample_categories,
        )
        assert result is expected
        self.classifier._agent.ainvoke.assert_called_once()

    def test_build_prompt_includes_file_name(self) -> None:
        prompt = self.classifier._build_prompt(
            file_name="LPA_Horizon.pdf",
            content="test content",
            categories=self.sample_categories,
            is_summary=False,
        )
        assert "LPA_Horizon.pdf" in prompt
        assert "LPA" in prompt
        assert "Subscription Agreement" in prompt
        assert "test content" in prompt
        assert "Document content" in prompt

    def test_build_prompt_summary_label(self) -> None:
        prompt = self.classifier._build_prompt(
            file_name="doc.pdf",
            content="summary text",
            categories=self.sample_categories,
            is_summary=True,
        )
        assert "Document summary" in prompt

    def test_filename_hint_lpa(self) -> None:
        assert self.classifier._get_filename_hint("LPA_Fund_IV.pdf") == "Limited Partnership Agreement"

    def test_filename_hint_subscription(self) -> None:
        assert self.classifier._get_filename_hint("Sub_Agreement_2024.pdf") == "Subscription Agreement"

    def test_filename_hint_side_letter(self) -> None:
        assert self.classifier._get_filename_hint("Side_Letter_LP1.pdf") == "Side Letter"

    def test_filename_hint_none(self) -> None:
        assert self.classifier._get_filename_hint("Document_001.pdf") is None

    def test_as_subagent_config(self) -> None:
        config = self.classifier.as_subagent_config()
        assert config["name"] == "classifier"
        assert config["description"]
        assert isinstance(config, dict)
