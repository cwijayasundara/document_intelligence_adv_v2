"""Tests for the parse service."""

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.parser.reducto import ReductoClient
from src.services.parse_service import ParseService
from src.services.state_machine import InvalidTransitionError


def _make_mock_doc(
    doc_id: uuid.UUID | None = None,
    status: str = "uploaded",
    parsed_path: str | None = None,
    original_path: str = "/tmp/test.pdf",
    file_name: str = "test.pdf",
) -> MagicMock:
    """Create a mock Document object."""
    doc = MagicMock()
    doc.id = doc_id or uuid.uuid4()
    doc.status = status
    doc.parsed_path = parsed_path
    doc.original_path = original_path
    doc.file_name = file_name
    doc.file_hash = "abc123"
    return doc


class TestParseService:
    """Tests for ParseService."""

    def setup_method(self) -> None:
        self.repo = MagicMock()
        self.repo._session = MagicMock()
        self.repo._session.flush = AsyncMock()

        self.storage = MagicMock()
        self.storage.parsed_dir = Path("/tmp/parsed")

        self.reducto = MagicMock(spec=ReductoClient)
        self.reducto.parse = AsyncMock(return_value="# Parsed content")

        self.service = ParseService(
            repo=self.repo,
            storage=self.storage,
            reducto_client=self.reducto,
        )

    @pytest.mark.asyncio
    async def test_parse_document_success(self, tmp_path: Path) -> None:
        doc_id = uuid.uuid4()
        doc = _make_mock_doc(doc_id=doc_id, status="uploaded")
        self.repo.get_by_id = AsyncMock(return_value=doc)
        self.storage.parsed_dir = tmp_path

        doc_result, content, skipped = await self.service.parse_document(doc_id)
        assert content == "# Parsed content"
        assert skipped is False
        assert doc.status == "parsed"

    @pytest.mark.asyncio
    async def test_parse_document_skips_if_exists(self, tmp_path: Path) -> None:
        doc_id = uuid.uuid4()
        parsed_file = tmp_path / "test.md"
        parsed_file.write_text("# Cached content")

        doc = _make_mock_doc(doc_id=doc_id, status="parsed", parsed_path=str(parsed_file))
        self.repo.get_by_id = AsyncMock(return_value=doc)
        self.storage.parsed_dir = tmp_path

        doc_result, content, skipped = await self.service.parse_document(doc_id)
        assert content == "# Cached content"
        assert skipped is True

    @pytest.mark.asyncio
    async def test_parse_document_not_found(self) -> None:
        self.repo.get_by_id = AsyncMock(return_value=None)
        with pytest.raises(ValueError, match="not found"):
            await self.service.parse_document(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_parse_invalid_transition(self, tmp_path: Path) -> None:
        doc_id = uuid.uuid4()
        doc = _make_mock_doc(doc_id=doc_id, status="classified")
        self.repo.get_by_id = AsyncMock(return_value=doc)
        self.storage.parsed_dir = tmp_path

        with pytest.raises(InvalidTransitionError):
            await self.service.parse_document(doc_id)

    @pytest.mark.asyncio
    async def test_get_parsed_content(self, tmp_path: Path) -> None:
        doc_id = uuid.uuid4()
        parsed_file = tmp_path / f"{doc_id}.md"
        parsed_file.write_text("# Content")

        doc = _make_mock_doc(doc_id=doc_id, parsed_path=str(parsed_file))
        self.repo.get_by_id = AsyncMock(return_value=doc)

        content = await self.service.get_parsed_content(doc_id)
        assert content == "# Content"

    @pytest.mark.asyncio
    async def test_get_parsed_content_not_found(self) -> None:
        self.repo.get_by_id = AsyncMock(return_value=None)
        content = await self.service.get_parsed_content(uuid.uuid4())
        assert content is None

    @pytest.mark.asyncio
    async def test_get_parsed_content_no_parsed_path(self) -> None:
        doc = _make_mock_doc(parsed_path=None)
        self.repo.get_by_id = AsyncMock(return_value=doc)
        content = await self.service.get_parsed_content(doc.id)
        assert content is None

    @pytest.mark.asyncio
    async def test_save_edited_content(self, tmp_path: Path) -> None:
        doc_id = uuid.uuid4()
        doc = _make_mock_doc(doc_id=doc_id, status="parsed")
        self.repo.get_by_id = AsyncMock(return_value=doc)
        self.storage.parsed_dir = tmp_path

        result = await self.service.save_edited_content(doc_id, "# Edited")
        assert result.status == "edited"

        saved_content = (tmp_path / "test.md").read_text()
        assert saved_content == "# Edited"

    @pytest.mark.asyncio
    async def test_save_edited_invalid_transition(self, tmp_path: Path) -> None:
        doc = _make_mock_doc(status="uploaded")
        self.repo.get_by_id = AsyncMock(return_value=doc)
        self.storage.parsed_dir = tmp_path

        with pytest.raises(InvalidTransitionError):
            await self.service.save_edited_content(doc.id, "# Edited")

    @pytest.mark.asyncio
    async def test_save_edited_not_found(self) -> None:
        self.repo.get_by_id = AsyncMock(return_value=None)
        with pytest.raises(ValueError, match="not found"):
            await self.service.save_edited_content(uuid.uuid4(), "# Edited")
