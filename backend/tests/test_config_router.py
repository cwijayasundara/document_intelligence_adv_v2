"""Tests for the config API router (categories and extraction fields)."""

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


def _mock_category(
    cat_id: uuid.UUID | None = None,
    name: str = "LPA",
) -> MagicMock:
    mock = MagicMock()
    mock.id = cat_id or uuid.uuid4()
    mock.name = name
    mock.description = "Test description"
    mock.classification_criteria = "Test criteria"
    mock.created_at = datetime(2026, 3, 28, tzinfo=timezone.utc)
    mock.updated_at = datetime(2026, 3, 28, tzinfo=timezone.utc)
    return mock


@patch("src.api.routers.config.CategoryRepository")
async def test_list_categories(MockRepo: MagicMock, client: AsyncClient) -> None:
    """GET /config/categories returns all categories."""
    instance = MockRepo.return_value
    instance.list_all = AsyncMock(return_value=[_mock_category()])

    response = await client.get("/api/v1/config/categories")

    assert response.status_code == 200
    data = response.json()
    assert len(data["categories"]) == 1
    assert data["categories"][0]["name"] == "LPA"


@patch("src.api.routers.config.CategoryRepository")
async def test_create_category(MockRepo: MagicMock, client: AsyncClient) -> None:
    """POST /config/categories creates a new category."""
    instance = MockRepo.return_value
    instance.create = AsyncMock(return_value=_mock_category(name="Sub Agreement"))

    response = await client.post(
        "/api/v1/config/categories",
        json={
            "name": "Sub Agreement",
            "description": "Subscription docs",
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Sub Agreement"


@patch("src.api.routers.config.CategoryRepository")
async def test_update_category(MockRepo: MagicMock, client: AsyncClient) -> None:
    """PUT /config/categories/:id updates a category."""
    cat_id = uuid.uuid4()
    instance = MockRepo.return_value
    instance.update = AsyncMock(return_value=_mock_category(cat_id=cat_id, name="Updated"))

    response = await client.put(
        f"/api/v1/config/categories/{cat_id}",
        json={"name": "Updated"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated"


@patch("src.api.routers.config.CategoryRepository")
async def test_update_category_not_found(MockRepo: MagicMock, client: AsyncClient) -> None:
    """PUT /config/categories/:id returns 404 for missing category."""
    instance = MockRepo.return_value
    instance.update = AsyncMock(return_value=None)

    response = await client.put(
        f"/api/v1/config/categories/{uuid.uuid4()}",
        json={"name": "Nope"},
    )

    assert response.status_code == 404


@patch("src.api.routers.config.DocumentRepository")
@patch("src.api.routers.config.CategoryRepository")
async def test_delete_category(
    MockCatRepo: MagicMock,
    MockDocRepo: MagicMock,
    client: AsyncClient,
) -> None:
    """DELETE /config/categories/:id returns 204."""
    cat_id = uuid.uuid4()
    cat_instance = MockCatRepo.return_value
    cat_instance.get_by_id = AsyncMock(return_value=_mock_category(cat_id=cat_id))
    cat_instance.delete = AsyncMock(return_value=True)

    doc_instance = MockDocRepo.return_value
    doc_instance.count_by_category = AsyncMock(return_value=0)

    response = await client.delete(f"/api/v1/config/categories/{cat_id}")

    assert response.status_code == 204


@patch("src.api.routers.config.DocumentRepository")
@patch("src.api.routers.config.CategoryRepository")
async def test_delete_category_with_documents(
    MockCatRepo: MagicMock,
    MockDocRepo: MagicMock,
    client: AsyncClient,
) -> None:
    """DELETE /config/categories/:id returns 400 if documents assigned."""
    cat_id = uuid.uuid4()
    cat_instance = MockCatRepo.return_value
    cat_instance.get_by_id = AsyncMock(return_value=_mock_category(cat_id=cat_id))

    doc_instance = MockDocRepo.return_value
    doc_instance.count_by_category = AsyncMock(return_value=5)

    response = await client.delete(f"/api/v1/config/categories/{cat_id}")

    assert response.status_code == 400
    assert "assigned documents" in response.json()["detail"]


@patch("src.api.routers.config.CategoryRepository")
async def test_delete_category_not_found(MockCatRepo: MagicMock, client: AsyncClient) -> None:
    """DELETE /config/categories/:id returns 404 for missing category."""
    cat_instance = MockCatRepo.return_value
    cat_instance.get_by_id = AsyncMock(return_value=None)

    response = await client.delete(f"/api/v1/config/categories/{uuid.uuid4()}")

    assert response.status_code == 404
