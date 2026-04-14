"""Tests for classifier module-level function."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.classifier import (
    _build_prompt,
    _get_filename_hint,
    classify_document,
)
from src.agents.schemas.classification import ClassificationResult


def _mk_llm(result: ClassificationResult | None) -> MagicMock:
    """Build a mock LLM whose with_structured_output(...).ainvoke returns `result`."""
    mock_structured = AsyncMock()
    mock_structured.ainvoke = AsyncMock(return_value=result)
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    return mock_llm


class TestClassifyDocument:
    """Tests for classify_document()."""

    sample_categories = [
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
    sample_content = (
        "# Limited Partnership Agreement\n\n"
        "This agreement establishes Horizon Equity Partners IV..."
    )

    @pytest.mark.asyncio
    async def test_classify_returns_result(self) -> None:
        expected = ClassificationResult(
            category_id=self.sample_categories[0]["id"],
            category_name="LPA",
            confidence=95,
            reasoning="matched based on partnership language",
        )
        mock_llm = _mk_llm(expected)
        with (
            patch("src.agents.classifier.get_llm", return_value=mock_llm),
            patch(
                "src.agents.classifier._load_learned_corrections",
                return_value="",
            ),
        ):
            result = await classify_document(
                file_name="LPA_Fund.pdf",
                content=self.sample_content,
                categories=self.sample_categories,
            )
        assert isinstance(result, ClassificationResult)
        assert result.category_name == "LPA"
        assert 0 <= result.confidence <= 100
        assert result.reasoning

    @pytest.mark.asyncio
    async def test_classify_empty_categories(self) -> None:
        result = await classify_document(
            file_name="doc.pdf",
            content=self.sample_content,
            categories=[],
        )
        assert result.category_name == "Other/Unclassified"
        assert "No categories" in result.reasoning
        assert result.confidence == 0

    @pytest.mark.asyncio
    async def test_classify_with_summary_uses_summary_label(self) -> None:
        """When summary is provided, the prompt uses the summary content."""
        expected = ClassificationResult(
            category_id=self.sample_categories[0]["id"],
            category_name="LPA",
            confidence=90,
            reasoning="from summary",
        )
        mock_llm = _mk_llm(expected)
        with (
            patch("src.agents.classifier.get_llm", return_value=mock_llm),
            patch(
                "src.agents.classifier._load_learned_corrections",
                return_value="",
            ),
        ):
            result = await classify_document(
                file_name="LPA_Fund.pdf",
                content=self.sample_content,
                categories=self.sample_categories,
                summary="This is a Limited Partnership Agreement for Horizon Fund.",
            )

        assert isinstance(result, ClassificationResult)
        # Verify the prompt built for the LLM referenced the summary label
        call_args = mock_llm.with_structured_output.return_value.ainvoke.call_args
        messages = call_args[0][0]
        prompt_text = messages[-1].content
        assert "Document summary" in prompt_text

    @pytest.mark.asyncio
    async def test_classify_fallback_on_none_result(self) -> None:
        """If structured output returns None, fallback parser kicks in."""
        mock_llm = _mk_llm(None)
        with (
            patch("src.agents.classifier.get_llm", return_value=mock_llm),
            patch(
                "src.agents.classifier._load_learned_corrections",
                return_value="",
            ),
        ):
            result = await classify_document(
                file_name="doc.pdf",
                content=self.sample_content,
                categories=self.sample_categories,
            )
        assert isinstance(result, ClassificationResult)
        # Fallback uses first category as final fallback when no text match
        assert result.category_id in [c["id"] for c in self.sample_categories]


class TestFilenameHints:
    """Tests for _get_filename_hint()."""

    def test_lpa(self) -> None:
        assert (
            _get_filename_hint("LPA Fund IV.pdf")
            == "Limited Partnership Agreement"
        )

    def test_subscription(self) -> None:
        assert (
            _get_filename_hint("Sub_Agreement_2024.pdf") == "Subscription Agreement"
        )

    def test_side_letter(self) -> None:
        assert _get_filename_hint("Side Letter LP1.pdf") == "Side Letter"

    def test_no_match(self) -> None:
        assert _get_filename_hint("Document_001.pdf") is None


class TestBuildPrompt:
    """Tests for _build_prompt()."""

    sample_categories = [
        {
            "id": uuid.uuid4(),
            "name": "LPA",
            "classification_criteria": "Limited Partnership Agreement",
        },
        {
            "id": uuid.uuid4(),
            "name": "Subscription Agreement",
            "classification_criteria": "Investor subscription",
        },
    ]

    def test_prompt_includes_file_name_and_content(self) -> None:
        prompt = _build_prompt(
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

    def test_prompt_summary_label(self) -> None:
        prompt = _build_prompt(
            file_name="doc.pdf",
            content="summary text",
            categories=self.sample_categories,
            is_summary=True,
        )
        assert "Document summary" in prompt
