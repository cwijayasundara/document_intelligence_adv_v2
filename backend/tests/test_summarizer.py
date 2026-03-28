"""Tests for summarizer subagent and summary service."""

import uuid
from unittest.mock import AsyncMock

import pytest

from src.agents.schemas.summary import SummaryResult
from src.agents.summarizer import SummarizerSubagent
from src.services.summarize_service import SummaryService


class TestSummarizerSubagent:
    """Tests for SummarizerSubagent."""

    def setup_method(self) -> None:
        self.summarizer = SummarizerSubagent()
        self.sample_content = (
            "# Limited Partnership Agreement\n\n"
            "This agreement establishes a fund with a management fee "
            "of 2% and carried interest of 20%."
        )

    @pytest.mark.asyncio
    async def test_summarize_returns_result(self) -> None:
        result = await self.summarizer.summarize(self.sample_content)
        assert isinstance(result, SummaryResult)
        assert result.summary
        assert isinstance(result.key_topics, list)

    @pytest.mark.asyncio
    async def test_summarize_extracts_topics(self) -> None:
        result = await self.summarizer.summarize(self.sample_content)
        assert len(result.key_topics) > 0

    @pytest.mark.asyncio
    async def test_summarize_applies_pii_filter(self) -> None:
        content = "SSN: 123-45-6789\n" + self.sample_content
        await self.summarizer.summarize(content)
        assert "123-45-6789" not in self.summarizer._parsed_content

    @pytest.mark.asyncio
    async def test_summarize_with_mock_agent(self) -> None:
        self.summarizer._agent.run = AsyncMock(return_value={"response": "Test summary"})
        result = await self.summarizer.summarize(self.sample_content)
        assert result.summary == "Test summary"

    def test_as_subagent_slot(self) -> None:
        slot = self.summarizer.as_subagent_slot()
        assert slot.name == "summarizer"
        assert slot.description

    @pytest.mark.asyncio
    async def test_get_parsed_content_tool(self) -> None:
        self.summarizer._parsed_content = "test"
        content = await self.summarizer._get_parsed_content()
        assert content == "test"

    def test_extract_topics_finds_keywords(self) -> None:
        topics = SummarizerSubagent._extract_topics("fund management fee carried interest")
        assert "fund" in topics
        assert "management fee" in topics

    def test_extract_topics_no_keywords(self) -> None:
        topics = SummarizerSubagent._extract_topics("hello world")
        assert topics == ["general"]


class TestSummaryService:
    """Tests for SummaryService."""

    def setup_method(self) -> None:
        self.mock_summarizer = SummarizerSubagent()
        self.mock_summarizer._agent.run = AsyncMock(return_value={"response": "Test summary"})
        self.service = SummaryService(summarizer=self.mock_summarizer)

    @pytest.mark.asyncio
    async def test_generate_summary(self) -> None:
        doc_id = uuid.uuid4()
        result = await self.service.generate_summary(doc_id, "test content")
        assert result["summary"]
        assert result["content_hash"]
        assert result["cached"] is False

    @pytest.mark.asyncio
    async def test_generate_summary_caches(self) -> None:
        doc_id = uuid.uuid4()
        await self.service.generate_summary(doc_id, "test content")
        result = await self.service.generate_summary(doc_id, "test content")
        assert result["cached"] is True

    @pytest.mark.asyncio
    async def test_regenerate_on_hash_change(self) -> None:
        doc_id = uuid.uuid4()
        await self.service.generate_summary(doc_id, "content v1")
        result = await self.service.generate_summary(doc_id, "content v2")
        assert result["cached"] is False

    def test_get_cached_summary(self) -> None:
        assert self.service.get_cached_summary(uuid.uuid4()) is None

    @pytest.mark.asyncio
    async def test_get_cached_summary_after_generate(self) -> None:
        doc_id = uuid.uuid4()
        await self.service.generate_summary(doc_id, "test")
        cached = self.service.get_cached_summary(doc_id)
        assert cached is not None
        assert cached["summary"]

    def test_compute_hash_deterministic(self) -> None:
        h1 = SummaryService._compute_hash("test")
        h2 = SummaryService._compute_hash("test")
        assert h1 == h2

    def test_compute_hash_different_for_different_content(self) -> None:
        h1 = SummaryService._compute_hash("test1")
        h2 = SummaryService._compute_hash("test2")
        assert h1 != h2
