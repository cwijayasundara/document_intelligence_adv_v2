"""Tests for RAG query API router endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app
from src.api.dependencies import get_session


@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session


@pytest.fixture
def app(mock_session) -> FastAPI:
    application = create_app(database_url="")

    async def _override_session():
        yield mock_session

    application.dependency_overrides[get_session] = _override_session
    return application


@pytest.fixture
async def client(app: FastAPI):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestRAGRouter:
    """Tests for POST /rag/query endpoint."""

    @pytest.mark.asyncio
    async def test_rag_query_success(self, client: AsyncClient) -> None:
        with (
            patch("src.api.routers.rag.get_app_settings") as mock_settings,
            patch("src.api.routers.rag.WeaviateClient") as mock_wc_cls,
            patch("src.api.routers.rag.RAGService") as mock_svc_cls,
        ):
            settings = MagicMock()
            settings.weaviate_url = "http://test:8080"
            mock_settings.return_value = settings

            mock_wc = MagicMock()
            mock_wc.connect = AsyncMock()
            mock_wc_cls.return_value = mock_wc

            mock_service = MagicMock()
            mock_service.query = AsyncMock(
                return_value={
                    "answer": "The fee is 2%",
                    "citations": [
                        {
                            "chunk_text": "Fee is 2%",
                            "document_name": "lpa.pdf",
                            "document_id": "doc-1",
                            "chunk_index": 0,
                            "relevance_score": 0.9,
                        }
                    ],
                    "search_mode": "hybrid",
                    "chunks_retrieved": 1,
                }
            )
            mock_svc_cls.return_value = mock_service

            resp = await client.post(
                "/api/v1/rag/query",
                json={
                    "query": "What is the management fee?",
                    "scope": "single_document",
                    "scope_id": "doc-1",
                    "search_mode": "hybrid",
                    "top_k": 5,
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["answer"] == "The fee is 2%"
            assert len(data["citations"]) == 1
            assert data["chunks_retrieved"] == 1

    @pytest.mark.asyncio
    async def test_rag_query_all_scope(self, client: AsyncClient) -> None:
        with (
            patch("src.api.routers.rag.get_app_settings") as mock_settings,
            patch("src.api.routers.rag.WeaviateClient") as mock_wc_cls,
            patch("src.api.routers.rag.RAGService") as mock_svc_cls,
        ):
            settings = MagicMock()
            settings.weaviate_url = "http://test:8080"
            mock_settings.return_value = settings

            mock_wc = MagicMock()
            mock_wc.connect = AsyncMock()
            mock_wc_cls.return_value = mock_wc

            mock_service = MagicMock()
            mock_service.query = AsyncMock(
                return_value={
                    "answer": "No results",
                    "citations": [],
                    "search_mode": "keyword",
                    "chunks_retrieved": 0,
                }
            )
            mock_svc_cls.return_value = mock_service

            resp = await client.post(
                "/api/v1/rag/query",
                json={
                    "query": "test",
                    "scope": "all",
                    "search_mode": "keyword",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["chunks_retrieved"] == 0

    @pytest.mark.asyncio
    async def test_rag_query_missing_query(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/rag/query",
            json={"scope": "all"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_rag_query_missing_scope(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/rag/query",
            json={"query": "test"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_rag_query_default_params(self, client: AsyncClient) -> None:
        with (
            patch("src.api.routers.rag.get_app_settings") as mock_settings,
            patch("src.api.routers.rag.WeaviateClient") as mock_wc_cls,
            patch("src.api.routers.rag.RAGService") as mock_svc_cls,
        ):
            settings = MagicMock()
            settings.weaviate_url = "http://test:8080"
            mock_settings.return_value = settings

            mock_wc = MagicMock()
            mock_wc.connect = AsyncMock()
            mock_wc_cls.return_value = mock_wc

            mock_service = MagicMock()
            mock_service.query = AsyncMock(
                return_value={
                    "answer": "Answer",
                    "citations": [],
                    "search_mode": "hybrid",
                    "chunks_retrieved": 0,
                }
            )
            mock_svc_cls.return_value = mock_service

            resp = await client.post(
                "/api/v1/rag/query",
                json={
                    "query": "test query",
                    "scope": "all",
                },
            )
            assert resp.status_code == 200
            call_kwargs = mock_service.query.call_args[1]
            assert call_kwargs["search_mode"] == "hybrid"
            assert call_kwargs["top_k"] == 5
