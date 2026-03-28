"""Tests for document service state machine integration."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.document_service import DocumentService
from src.services.state_machine import InvalidTransitionError


def _make_mock_doc(
    doc_id: uuid.UUID | None = None,
    status: str = "uploaded",
) -> MagicMock:
    doc = MagicMock()
    doc.id = doc_id or uuid.uuid4()
    doc.status = status
    doc.updated_at = datetime.now()
    return doc


class TestDocumentServiceStateMachine:
    """Tests for state machine methods in DocumentService."""

    def setup_method(self) -> None:
        self.session = MagicMock()
        self.session.flush = AsyncMock()
        self.storage = MagicMock()
        self.service = DocumentService(self.session, self.storage)
        self.service._repo = MagicMock()
        self.service._repo._session = self.session

    @pytest.mark.asyncio
    async def test_transition_status_success(self) -> None:
        doc = _make_mock_doc(status="uploaded")
        self.service._repo.get_by_id = AsyncMock(return_value=doc)

        result = await self.service.transition_status(doc.id, "parsed")
        assert result.status == "parsed"

    @pytest.mark.asyncio
    async def test_transition_status_not_found(self) -> None:
        self.service._repo.get_by_id = AsyncMock(return_value=None)
        with pytest.raises(ValueError, match="not found"):
            await self.service.transition_status(uuid.uuid4(), "parsed")

    @pytest.mark.asyncio
    async def test_transition_status_invalid(self) -> None:
        doc = _make_mock_doc(status="uploaded")
        self.service._repo.get_by_id = AsyncMock(return_value=doc)

        with pytest.raises(InvalidTransitionError):
            await self.service.transition_status(doc.id, "classified")

    @pytest.mark.asyncio
    async def test_get_available_actions(self) -> None:
        doc = _make_mock_doc(status="parsed")
        self.service._repo.get_by_id = AsyncMock(return_value=doc)

        actions = await self.service.get_available_actions(doc.id)
        assert "edited" in actions
        assert "classified" in actions

    @pytest.mark.asyncio
    async def test_get_available_actions_not_found(self) -> None:
        self.service._repo.get_by_id = AsyncMock(return_value=None)
        with pytest.raises(ValueError, match="not found"):
            await self.service.get_available_actions(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_transition_uploaded_to_parsed(self) -> None:
        doc = _make_mock_doc(status="uploaded")
        self.service._repo.get_by_id = AsyncMock(return_value=doc)
        result = await self.service.transition_status(doc.id, "parsed")
        assert result.status == "parsed"

    @pytest.mark.asyncio
    async def test_transition_parsed_to_classified(self) -> None:
        doc = _make_mock_doc(status="parsed")
        self.service._repo.get_by_id = AsyncMock(return_value=doc)
        result = await self.service.transition_status(doc.id, "classified")
        assert result.status == "classified"

    @pytest.mark.asyncio
    async def test_transition_classified_to_extracted(self) -> None:
        doc = _make_mock_doc(status="classified")
        self.service._repo.get_by_id = AsyncMock(return_value=doc)
        result = await self.service.transition_status(doc.id, "extracted")
        assert result.status == "extracted"

    @pytest.mark.asyncio
    async def test_transition_extracted_to_summarized(self) -> None:
        doc = _make_mock_doc(status="extracted")
        self.service._repo.get_by_id = AsyncMock(return_value=doc)
        result = await self.service.transition_status(doc.id, "summarized")
        assert result.status == "summarized"

    @pytest.mark.asyncio
    async def test_transition_summarized_to_ingested(self) -> None:
        doc = _make_mock_doc(status="summarized")
        self.service._repo.get_by_id = AsyncMock(return_value=doc)
        result = await self.service.transition_status(doc.id, "ingested")
        assert result.status == "ingested"
