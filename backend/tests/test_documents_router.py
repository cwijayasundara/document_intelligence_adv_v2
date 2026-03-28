"""Tests for the documents API router endpoints."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.app import create_app
from src.api.dependencies import get_session


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def app(mock_session: AsyncMock) -> FastAPI:
    application = create_app(database_url="")

    async def override_session():
        yield mock_session

    application.dependency_overrides[get_session] = override_session
    return application


@pytest.fixture
async def client(app: FastAPI):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _make_mock_doc(
    doc_id: uuid.UUID | None = None,
    file_name: str = "test.pdf",
    status: str = "uploaded",
) -> MagicMock:
    """Create a mock Document object."""
    mock = MagicMock()
    mock.id = doc_id or uuid.uuid4()
    mock.file_name = file_name
    mock.original_path = f"/data/upload/{file_name}"
    mock.parsed_path = None
    mock.file_hash = "abc123"
    mock.status = status
    mock.document_category_id = None
    mock.file_type = "pdf"
    mock.file_size = 1024
    mock.created_at = datetime(2026, 3, 28, tzinfo=timezone.utc)
    mock.updated_at = datetime(2026, 3, 28, tzinfo=timezone.utc)
    return mock


@patch("src.api.routers.documents._get_storage")
@patch("src.api.routers.documents.DocumentService")
async def test_upload_document(
    MockService: MagicMock,
    mock_get_storage: MagicMock,
    client: AsyncClient,
) -> None:
    """POST /documents/upload creates a document."""
    mock_doc = _make_mock_doc()
    instance = MockService.return_value
    instance.upload = AsyncMock(return_value=(mock_doc, False))

    response = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.pdf", b"content", "application/pdf")},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["file_name"] == "test.pdf"


@patch("src.api.routers.documents._get_storage")
@patch("src.api.routers.documents.DocumentService")
async def test_list_documents(
    MockService: MagicMock,
    mock_get_storage: MagicMock,
    client: AsyncClient,
) -> None:
    """GET /documents returns list of documents."""
    mock_doc = _make_mock_doc()
    instance = MockService.return_value
    instance.list_documents = AsyncMock(return_value=([mock_doc], 1))

    response = await client.get("/api/v1/documents")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["documents"]) == 1


@patch("src.api.routers.documents._get_storage")
@patch("src.api.routers.documents.DocumentService")
async def test_get_document(
    MockService: MagicMock,
    mock_get_storage: MagicMock,
    client: AsyncClient,
) -> None:
    """GET /documents/:id returns document details."""
    doc_id = uuid.uuid4()
    mock_doc = _make_mock_doc(doc_id=doc_id)
    instance = MockService.return_value
    instance.get_document = AsyncMock(return_value=mock_doc)

    response = await client.get(f"/api/v1/documents/{doc_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(doc_id)


@patch("src.api.routers.documents._get_storage")
@patch("src.api.routers.documents.DocumentService")
async def test_get_document_not_found(
    MockService: MagicMock,
    mock_get_storage: MagicMock,
    client: AsyncClient,
) -> None:
    """GET /documents/:id returns 404 for missing document."""
    instance = MockService.return_value
    instance.get_document = AsyncMock(return_value=None)

    response = await client.get(f"/api/v1/documents/{uuid.uuid4()}")

    assert response.status_code == 404


@patch("src.api.routers.documents._get_storage")
@patch("src.api.routers.documents.DocumentService")
async def test_delete_document(
    MockService: MagicMock,
    mock_get_storage: MagicMock,
    client: AsyncClient,
) -> None:
    """DELETE /documents/:id returns 204 on success."""
    instance = MockService.return_value
    instance.delete_document = AsyncMock(return_value=True)

    response = await client.delete(f"/api/v1/documents/{uuid.uuid4()}")

    assert response.status_code == 204


@patch("src.api.routers.documents._get_storage")
@patch("src.api.routers.documents.DocumentService")
async def test_delete_document_not_found(
    MockService: MagicMock,
    mock_get_storage: MagicMock,
    client: AsyncClient,
) -> None:
    """DELETE /documents/:id returns 404 for missing document."""
    instance = MockService.return_value
    instance.delete_document = AsyncMock(return_value=False)

    response = await client.delete(f"/api/v1/documents/{uuid.uuid4()}")

    assert response.status_code == 404


@patch("src.api.routers.documents._get_storage")
@patch("src.api.routers.documents.DocumentService")
async def test_upload_invalid_type(
    MockService: MagicMock,
    mock_get_storage: MagicMock,
    client: AsyncClient,
) -> None:
    """POST /documents/upload returns 422 for invalid file type."""
    instance = MockService.return_value
    instance.upload = AsyncMock(side_effect=ValueError("File type 'exe' not allowed"))

    response = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.exe", b"bad", "application/octet-stream")},
    )

    assert response.status_code == 422
