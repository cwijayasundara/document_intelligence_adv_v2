"""Tests for classification API router endpoints."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.agents.schemas.classification import ClassificationResult
from src.api.app import create_app
from src.api.dependencies import get_session


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
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


class TestClassifyRouter:
    """Tests for POST /classify/:id endpoint."""

    @pytest.mark.asyncio
    async def test_classify_not_found(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        with patch("src.api.routers.classify.DocumentRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            resp = await client.post(f"/api/v1/classify/{doc_id}")
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_classify_invalid_transition(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.status = "uploaded"
        mock_doc.parsed_path = None

        with patch("src.api.routers.classify.DocumentRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
            mock_repo_cls.return_value = mock_repo

            resp = await client.post(f"/api/v1/classify/{doc_id}")
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_classify_no_parsed_content(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.status = "parsed"
        mock_doc.parsed_path = None

        with patch("src.api.routers.classify.DocumentRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
            mock_repo_cls.return_value = mock_repo

            resp = await client.post(f"/api/v1/classify/{doc_id}")
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_classify_success(self, client: AsyncClient, tmp_path) -> None:
        doc_id = uuid.uuid4()
        cat_id = uuid.uuid4()
        parsed_file = tmp_path / "test.md"
        parsed_file.write_text("# Test LPA Document")

        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.status = "parsed"
        mock_doc.parsed_path = str(parsed_file)

        mock_category = MagicMock()
        mock_category.id = cat_id
        mock_category.name = "LPA"
        mock_category.classification_criteria = "LPA criteria"

        classification_result = ClassificationResult(
            category_id=cat_id,
            category_name="LPA",
            reasoning="Document matches LPA pattern",
        )

        with (
            patch("src.api.routers.classify.DocumentRepository") as mock_repo_cls,
            patch("src.api.routers.classify.CategoryRepository") as mock_cat_cls,
            patch("src.api.routers.classify._get_classifier") as mock_get_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
            mock_repo_cls.return_value = mock_repo

            mock_cat_repo = MagicMock()
            mock_cat_repo.list_all = AsyncMock(return_value=[mock_category])
            mock_cat_cls.return_value = mock_cat_repo

            mock_classifier = MagicMock()
            mock_classifier.classify = AsyncMock(return_value=classification_result)
            mock_get_cls.return_value = mock_classifier

            resp = await client.post(f"/api/v1/classify/{doc_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["category_name"] == "LPA"
            assert data["reasoning"] == "Document matches LPA pattern"
            assert data["status"] == "classified"

    @pytest.mark.asyncio
    async def test_classify_from_edited_status(self, client: AsyncClient, tmp_path) -> None:
        """Verify classification works from 'edited' status too."""
        doc_id = uuid.uuid4()
        cat_id = uuid.uuid4()
        parsed_file = tmp_path / "test.md"
        parsed_file.write_text("# Edited content")

        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.status = "edited"
        mock_doc.parsed_path = str(parsed_file)

        classification_result = ClassificationResult(
            category_id=cat_id,
            category_name="Subscription Agreement",
            reasoning="Matches subscription pattern",
        )

        with (
            patch("src.api.routers.classify.DocumentRepository") as mock_repo_cls,
            patch("src.api.routers.classify.CategoryRepository") as mock_cat_cls,
            patch("src.api.routers.classify._get_classifier") as mock_get_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
            mock_repo_cls.return_value = mock_repo

            mock_cat_repo = MagicMock()
            mock_cat_repo.list_all = AsyncMock(return_value=[])
            mock_cat_cls.return_value = mock_cat_repo

            mock_classifier = MagicMock()
            mock_classifier.classify = AsyncMock(return_value=classification_result)
            mock_get_cls.return_value = mock_classifier

            resp = await client.post(f"/api/v1/classify/{doc_id}")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_classify_parsed_file_missing(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.status = "parsed"
        mock_doc.parsed_path = "/nonexistent/path.md"

        with patch("src.api.routers.classify.DocumentRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
            mock_repo_cls.return_value = mock_repo

            resp = await client.post(f"/api/v1/classify/{doc_id}")
            assert resp.status_code == 404
