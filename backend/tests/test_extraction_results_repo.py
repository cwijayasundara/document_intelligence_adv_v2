"""Tests for ExtractedValuesRepository."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.db.repositories.extracted_values import ExtractedValuesRepository


class TestExtractedValuesRepository:
    """Tests for extraction results repository operations."""

    @pytest.mark.asyncio
    async def test_save_results(self) -> None:
        """Test saving extraction results."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        repo = ExtractedValuesRepository(session)
        doc_id = uuid.uuid4()
        field_id = uuid.uuid4()

        results = [
            {
                "field_id": field_id,
                "extracted_value": "Test Fund IV",
                "source_text": "...Test Fund IV...",
                "confidence": "high",
                "confidence_reasoning": "Explicit match",
                "requires_review": False,
            }
        ]

        saved = await repo.save_results(doc_id, results)
        assert len(saved) == 1
        assert saved[0].document_id == doc_id
        assert saved[0].field_id == field_id
        assert saved[0].extracted_value == "Test Fund IV"
        assert saved[0].confidence == "high"
        assert saved[0].reviewed is False
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_save_results_with_review(self) -> None:
        """Test saving results that require review."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        repo = ExtractedValuesRepository(session)
        doc_id = uuid.uuid4()

        results = [
            {
                "field_id": uuid.uuid4(),
                "extracted_value": "10 years",
                "source_text": "...not to exceed ten years...",
                "confidence": "low",
                "confidence_reasoning": "Multiple interpretations",
                "requires_review": True,
            }
        ]

        saved = await repo.save_results(doc_id, results)
        assert saved[0].requires_review is True
        assert saved[0].reviewed is False

    @pytest.mark.asyncio
    async def test_save_multiple_results(self) -> None:
        """Test saving multiple extraction results."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        repo = ExtractedValuesRepository(session)
        doc_id = uuid.uuid4()

        results = [
            {
                "field_id": uuid.uuid4(),
                "extracted_value": "Value 1",
                "source_text": "Source 1",
                "confidence": "high",
                "confidence_reasoning": "Clear",
                "requires_review": False,
            },
            {
                "field_id": uuid.uuid4(),
                "extracted_value": "Value 2",
                "source_text": "Source 2",
                "confidence": "low",
                "confidence_reasoning": "Unclear",
                "requires_review": True,
            },
        ]

        saved = await repo.save_results(doc_id, results)
        assert len(saved) == 2
        assert session.add.call_count == 2

    @pytest.mark.asyncio
    async def test_get_by_document_id(self) -> None:
        """Test retrieving results by document ID."""
        mock_ev = MagicMock()
        mock_ev.document_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_ev]

        session = AsyncMock()
        session.execute = AsyncMock(return_value=mock_result)

        repo = ExtractedValuesRepository(session)
        values = await repo.get_by_document_id(mock_ev.document_id)
        assert len(values) == 1

    @pytest.mark.asyncio
    async def test_update_values(self) -> None:
        """Test updating extracted values and marking reviewed."""
        mock_result = MagicMock()
        mock_result.rowcount = 1

        session = AsyncMock()
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()

        repo = ExtractedValuesRepository(session)
        field_id = uuid.uuid4()

        updates = [
            {
                "field_id": field_id,
                "extracted_value": "Updated value",
                "reviewed": True,
            }
        ]

        count = await repo.update_values(updates)
        assert count == 1
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_unreviewed_fields(self) -> None:
        """Test getting field names that need review."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = ["fund_term"]

        session = AsyncMock()
        session.execute = AsyncMock(return_value=mock_result)

        repo = ExtractedValuesRepository(session)
        unreviewed = await repo.get_unreviewed_fields(uuid.uuid4())
        assert unreviewed == ["fund_term"]

    @pytest.mark.asyncio
    async def test_save_results_defaults(self) -> None:
        """Test saving results uses defaults for missing keys."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        repo = ExtractedValuesRepository(session)
        results = [{"field_id": uuid.uuid4()}]

        saved = await repo.save_results(uuid.uuid4(), results)
        assert saved[0].extracted_value == ""
        assert saved[0].confidence == "medium"
