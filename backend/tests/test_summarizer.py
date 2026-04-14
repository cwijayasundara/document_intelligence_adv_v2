"""Tests for summarizer function and summary service."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.schemas.summary import SummaryResult
from src.agents.summarizer import _extract_topics, summarize_document
from src.services.summarize_service import SummaryService


def _mk_llm(result: SummaryResult | None, raise_exc: Exception | None = None) -> MagicMock:
    """Build a mock LLM whose with_structured_output(...).ainvoke returns `result`."""
    mock_structured = AsyncMock()
    if raise_exc is not None:
        mock_structured.ainvoke = AsyncMock(side_effect=raise_exc)
    else:
        mock_structured.ainvoke = AsyncMock(return_value=result)
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    return mock_llm


class TestSummarizeDocument:
    """Tests for summarize_document function."""

    sample_content = (
        "# Limited Partnership Agreement\n\n"
        "This agreement establishes a fund with a management fee "
        "of 2% and carried interest of 20%."
    )

    @pytest.mark.asyncio
    async def test_summarize_returns_result(self) -> None:
        expected = SummaryResult(summary="Test summary", key_topics=["fund"])
        mock_llm = _mk_llm(expected)
        with patch("src.agents.summarizer.get_llm", return_value=mock_llm):
            result = await summarize_document(self.sample_content)
        assert isinstance(result, SummaryResult)
        assert result.summary == "Test summary"

    @pytest.mark.asyncio
    async def test_summarize_fallback_on_error(self) -> None:
        mock_llm = _mk_llm(None, raise_exc=Exception("parse error"))
        with patch("src.agents.summarizer.get_llm", return_value=mock_llm):
            result = await summarize_document(self.sample_content)
        assert isinstance(result, SummaryResult)
        assert len(result.key_topics) > 0

    @pytest.mark.asyncio
    async def test_summarize_applies_pii_filter(self) -> None:
        expected = SummaryResult(summary="Redacted summary", key_topics=["general"])
        mock_llm = _mk_llm(expected)
        with patch("src.agents.summarizer.get_llm", return_value=mock_llm):
            content = "SSN: 123-45-6789\n" + self.sample_content
            await summarize_document(content)

        # Inspect the prompt sent to the LLM — SSN should have been redacted
        call_args = mock_llm.with_structured_output.return_value.ainvoke.call_args
        messages = call_args[0][0]
        prompt_text = messages[-1].content
        assert "123-45-6789" not in prompt_text

    def test_extract_topics_finds_keywords(self) -> None:
        topics = _extract_topics("fund management fee carried interest")
        assert "fund" in topics
        assert "management fee" in topics

    def test_extract_topics_no_keywords(self) -> None:
        topics = _extract_topics("hello world")
        assert topics == ["general"]


class TestSummaryService:
    """Tests for SummaryService."""

    @pytest.mark.asyncio
    @patch("src.services.summarize_service.summarize_document")
    async def test_generate_summary(self, mock_summarize: AsyncMock) -> None:
        mock_summarize.return_value = SummaryResult(summary="Test summary", key_topics=["general"])
        service = SummaryService()
        doc_id = uuid.uuid4()
        result = await service.generate_summary(doc_id, "test content")
        assert result["summary"]
        assert result["content_hash"]
        assert result["cached"] is False

    @pytest.mark.asyncio
    @patch("src.services.summarize_service.summarize_document")
    async def test_generate_summary_caches(self, mock_summarize: AsyncMock) -> None:
        mock_summarize.return_value = SummaryResult(summary="Test summary", key_topics=["general"])
        service = SummaryService()
        doc_id = uuid.uuid4()
        await service.generate_summary(doc_id, "test content")
        result = await service.generate_summary(doc_id, "test content")
        assert result["cached"] is True

    @pytest.mark.asyncio
    @patch("src.services.summarize_service.summarize_document")
    async def test_regenerate_on_hash_change(self, mock_summarize: AsyncMock) -> None:
        mock_summarize.return_value = SummaryResult(summary="Test summary", key_topics=["general"])
        service = SummaryService()
        doc_id = uuid.uuid4()
        await service.generate_summary(doc_id, "content v1")
        result = await service.generate_summary(doc_id, "content v2")
        assert result["cached"] is False

    def test_compute_hash_deterministic(self) -> None:
        h1 = SummaryService._compute_hash("test")
        h2 = SummaryService._compute_hash("test")
        assert h1 == h2

    def test_compute_hash_different_for_different_content(self) -> None:
        h1 = SummaryService._compute_hash("test1")
        h2 = SummaryService._compute_hash("test2")
        assert h1 != h2
