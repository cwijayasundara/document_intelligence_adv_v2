"""Tests for parse API router endpoints."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app
from src.services.state_machine import InvalidTransitionError


@pytest.fixture
def app() -> FastAPI:
    return create_app(database_url="")


@pytest.fixture
async def client(app: FastAPI):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestParseRouter:
    """Tests for parse API endpoints."""

    @pytest.mark.asyncio
    async def test_parse_document_not_found(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        with patch(
            "src.api.routers.parse._build_parse_service"
        ) as mock_build:
            service = MagicMock()
            service.parse_document = AsyncMock(
                side_effect=ValueError(f"Document {doc_id} not found")
            )
            mock_build.return_value = service

            resp = await client.post(f"/api/v1/parse/{doc_id}")
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_parse_document_invalid_transition(
        self, client: AsyncClient
    ) -> None:
        doc_id = uuid.uuid4()
        with patch(
            "src.api.routers.parse._build_parse_service"
        ) as mock_build:
            service = MagicMock()
            service.parse_document = AsyncMock(
                side_effect=InvalidTransitionError("classified", "parsed")
            )
            mock_build.return_value = service

            resp = await client.post(f"/api/v1/parse/{doc_id}")
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_parse_document_success(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.status = "parsed"

        with patch(
            "src.api.routers.parse._build_parse_service"
        ) as mock_build:
            service = MagicMock()
            service.parse_document = AsyncMock(
                return_value=(mock_doc, "# Content", False)
            )
            mock_build.return_value = service

            resp = await client.post(f"/api/v1/parse/{doc_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["content"] == "# Content"
            assert data["skipped"] is False

    @pytest.mark.asyncio
    async def test_parse_document_cached(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.status = "parsed"

        with patch(
            "src.api.routers.parse._build_parse_service"
        ) as mock_build:
            service = MagicMock()
            service.parse_document = AsyncMock(
                return_value=(mock_doc, "# Cached", True)
            )
            mock_build.return_value = service

            resp = await client.post(f"/api/v1/parse/{doc_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["skipped"] is True
            assert data["message"] is not None

    @pytest.mark.asyncio
    async def test_get_content_not_found(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        with patch(
            "src.api.routers.parse._build_parse_service"
        ) as mock_build, patch(
            "src.api.routers.parse.DocumentRepository"
        ) as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            service = MagicMock()
            mock_build.return_value = service

            resp = await client.get(f"/api/v1/parse/{doc_id}/content")
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_content_success(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.status = "parsed"

        with patch(
            "src.api.routers.parse._build_parse_service"
        ) as mock_build, patch(
            "src.api.routers.parse.DocumentRepository"
        ) as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
            mock_repo_cls.return_value = mock_repo

            service = MagicMock()
            service.get_parsed_content = AsyncMock(return_value="# Content")
            mock_build.return_value = service

            resp = await client.get(f"/api/v1/parse/{doc_id}/content")
            assert resp.status_code == 200
            data = resp.json()
            assert data["content"] == "# Content"

    @pytest.mark.asyncio
    async def test_put_content_success(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.status = "edited"

        with patch(
            "src.api.routers.parse._build_parse_service"
        ) as mock_build:
            service = MagicMock()
            service.save_edited_content = AsyncMock(return_value=mock_doc)
            mock_build.return_value = service

            resp = await client.put(
                f"/api/v1/parse/{doc_id}/content",
                json={"content": "# Edited"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "edited"
            assert data["content_length"] == 8

    @pytest.mark.asyncio
    async def test_put_content_invalid_transition(
        self, client: AsyncClient
    ) -> None:
        doc_id = uuid.uuid4()
        with patch(
            "src.api.routers.parse._build_parse_service"
        ) as mock_build:
            service = MagicMock()
            service.save_edited_content = AsyncMock(
                side_effect=InvalidTransitionError("uploaded", "edited")
            )
            mock_build.return_value = service

            resp = await client.put(
                f"/api/v1/parse/{doc_id}/content",
                json={"content": "# Edited"},
            )
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_parse_reducto_error(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        from src.parser.reducto import ReductoParseError

        with patch(
            "src.api.routers.parse._build_parse_service"
        ) as mock_build:
            service = MagicMock()
            service.parse_document = AsyncMock(
                side_effect=ReductoParseError("API failed")
            )
            mock_build.return_value = service

            resp = await client.post(f"/api/v1/parse/{doc_id}")
            assert resp.status_code == 500
