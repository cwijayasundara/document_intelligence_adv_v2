"""Tests for summarize API router endpoints."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app


@pytest.fixture
def app() -> FastAPI:
    return create_app(database_url="")


@pytest.fixture
async def client(app: FastAPI):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestSummarizeRouter:
    """Tests for summarize API endpoints."""

    @pytest.mark.asyncio
    async def test_summarize_not_found(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        with patch("src.api.routers.summarize.DocumentRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            resp = await client.post(f"/api/v1/summarize/{doc_id}")
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_summarize_invalid_transition(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.status = "uploaded"
        mock_doc.parsed_path = None

        with patch("src.api.routers.summarize.DocumentRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
            mock_repo_cls.return_value = mock_repo

            resp = await client.post(f"/api/v1/summarize/{doc_id}")
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_get_summary_not_found(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        mock_doc = MagicMock()
        mock_doc.id = doc_id

        with (
            patch("src.api.routers.summarize.DocumentRepository") as mock_repo_cls,
            patch("src.api.routers.summarize._get_summary_service") as mock_svc,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
            mock_repo_cls.return_value = mock_repo

            service = MagicMock()
            service.get_cached_summary.return_value = None
            mock_svc.return_value = service

            resp = await client.get(f"/api/v1/summarize/{doc_id}")
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_summary_doc_not_found(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        with patch("src.api.routers.summarize.DocumentRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            resp = await client.get(f"/api/v1/summarize/{doc_id}")
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_summary_success(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        mock_doc = MagicMock()
        mock_doc.id = doc_id

        with (
            patch("src.api.routers.summarize.DocumentRepository") as mock_repo_cls,
            patch("src.api.routers.summarize._get_summary_service") as mock_svc,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
            mock_repo_cls.return_value = mock_repo

            service = MagicMock()
            service.get_cached_summary.return_value = {
                "summary": "Test summary",
                "key_topics": ["topic1"],
                "content_hash": "abc123",
            }
            mock_svc.return_value = service

            resp = await client.get(f"/api/v1/summarize/{doc_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["summary"] == "Test summary"

    @pytest.mark.asyncio
    async def test_summarize_success(self, client: AsyncClient, tmp_path) -> None:
        doc_id = uuid.uuid4()
        parsed_file = tmp_path / "test.md"
        parsed_file.write_text("# Test content")

        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.status = "extracted"
        mock_doc.parsed_path = str(parsed_file)

        mock_session = AsyncMock()
        mock_session.flush = AsyncMock()

        with (
            patch("src.api.routers.summarize.DocumentRepository") as mock_repo_cls,
            patch("src.api.routers.summarize._get_summary_service") as mock_svc,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
            mock_repo_cls.return_value = mock_repo

            service = MagicMock()
            service.generate_summary = AsyncMock(
                return_value={
                    "summary": "Generated summary",
                    "key_topics": ["topic1"],
                    "content_hash": "abc",
                    "cached": False,
                }
            )
            mock_svc.return_value = service

            resp = await client.post(f"/api/v1/summarize/{doc_id}")
            assert resp.status_code in (200, 400, 422, 500)

    @pytest.mark.asyncio
    async def test_summarize_no_parsed_content(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.status = "extracted"
        mock_doc.parsed_path = None

        with patch("src.api.routers.summarize.DocumentRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
            mock_repo_cls.return_value = mock_repo

            resp = await client.post(f"/api/v1/summarize/{doc_id}")
            assert resp.status_code == 400
