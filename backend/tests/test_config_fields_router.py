"""Tests for config router extraction fields endpoints."""

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


def _mock_category(cat_id: uuid.UUID | None = None) -> MagicMock:
    mock = MagicMock()
    mock.id = cat_id or uuid.uuid4()
    mock.name = "LPA"
    mock.description = "Test"
    mock.classification_criteria = None
    mock.created_at = datetime(2026, 3, 28, tzinfo=timezone.utc)
    mock.updated_at = datetime(2026, 3, 28, tzinfo=timezone.utc)
    return mock


def _mock_schema(schema_id: uuid.UUID | None = None, version: int = 1) -> MagicMock:
    mock = MagicMock()
    mock.id = schema_id or uuid.uuid4()
    mock.version = version
    return mock


def _mock_field(field_name: str = "fund_name", sort_order: int = 1) -> MagicMock:
    mock = MagicMock()
    mock.id = uuid.uuid4()
    mock.field_name = field_name
    mock.display_name = field_name.replace("_", " ").title()
    mock.description = "Test field"
    mock.examples = "example"
    mock.data_type = "string"
    mock.required = True
    mock.sort_order = sort_order
    return mock


@patch("src.api.routers.config.ExtractionFieldRepository")
@patch("src.api.routers.config.ExtractionSchemaRepository")
@patch("src.api.routers.config.CategoryRepository")
async def test_list_fields(
    MockCatRepo: MagicMock,
    MockSchemaRepo: MagicMock,
    MockFieldRepo: MagicMock,
    client: AsyncClient,
) -> None:
    """GET /config/categories/:id/fields returns extraction fields."""
    cat_id = uuid.uuid4()
    cat_instance = MockCatRepo.return_value
    cat_instance.get_by_id = AsyncMock(return_value=_mock_category(cat_id))

    schema = _mock_schema(version=2)
    schema_instance = MockSchemaRepo.return_value
    schema_instance.get_latest_for_category = AsyncMock(return_value=schema)

    field_instance = MockFieldRepo.return_value
    field_instance.get_fields_for_schema = AsyncMock(
        return_value=[_mock_field("fund_name", 1), _mock_field("fee_rate", 2)]
    )

    response = await client.get(f"/api/v1/config/categories/{cat_id}/fields")

    assert response.status_code == 200
    data = response.json()
    assert data["category_name"] == "LPA"
    assert data["schema_version"] == 2
    assert len(data["fields"]) == 2


@patch("src.api.routers.config.ExtractionSchemaRepository")
@patch("src.api.routers.config.CategoryRepository")
async def test_list_fields_no_schema(
    MockCatRepo: MagicMock,
    MockSchemaRepo: MagicMock,
    client: AsyncClient,
) -> None:
    """GET /config/categories/:id/fields returns empty when no schema."""
    cat_id = uuid.uuid4()
    cat_instance = MockCatRepo.return_value
    cat_instance.get_by_id = AsyncMock(return_value=_mock_category(cat_id))

    schema_instance = MockSchemaRepo.return_value
    schema_instance.get_latest_for_category = AsyncMock(return_value=None)

    response = await client.get(f"/api/v1/config/categories/{cat_id}/fields")

    assert response.status_code == 200
    data = response.json()
    assert data["schema_version"] == 0
    assert data["fields"] == []


@patch("src.api.routers.config.CategoryRepository")
async def test_list_fields_category_not_found(
    MockCatRepo: MagicMock,
    client: AsyncClient,
) -> None:
    """GET /config/categories/:id/fields returns 404 for missing category."""
    cat_instance = MockCatRepo.return_value
    cat_instance.get_by_id = AsyncMock(return_value=None)

    response = await client.get(
        f"/api/v1/config/categories/{uuid.uuid4()}/fields"
    )

    assert response.status_code == 404


@patch("src.api.routers.config.ExtractionFieldRepository")
@patch("src.api.routers.config.ExtractionSchemaRepository")
@patch("src.api.routers.config.CategoryRepository")
async def test_create_fields(
    MockCatRepo: MagicMock,
    MockSchemaRepo: MagicMock,
    MockFieldRepo: MagicMock,
    mock_session: AsyncMock,
    client: AsyncClient,
) -> None:
    """POST /config/categories/:id/fields creates fields."""
    cat_id = uuid.uuid4()
    cat_instance = MockCatRepo.return_value
    cat_instance.get_by_id = AsyncMock(return_value=_mock_category(cat_id))

    schema = _mock_schema(version=1)
    schema_instance = MockSchemaRepo.return_value
    schema_instance.get_next_version = AsyncMock(return_value=1)
    schema_instance.create = AsyncMock(return_value=schema)
    schema_instance.get_latest_for_category = AsyncMock(return_value=None)

    field_instance = MockFieldRepo.return_value
    field_instance.upsert_field = AsyncMock(return_value=_mock_field())

    response = await client.post(
        f"/api/v1/config/categories/{cat_id}/fields",
        json={
            "fields": [
                {
                    "field_name": "fund_name",
                    "display_name": "Fund Name",
                    "data_type": "string",
                    "required": True,
                    "sort_order": 1,
                }
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["schema_version"] == 1
    assert data["fields_created"] == 1


@patch("src.api.routers.config.CategoryRepository")
async def test_create_fields_category_not_found(
    MockCatRepo: MagicMock,
    client: AsyncClient,
) -> None:
    """POST /config/categories/:id/fields returns 404 for missing cat."""
    cat_instance = MockCatRepo.return_value
    cat_instance.get_by_id = AsyncMock(return_value=None)

    response = await client.post(
        f"/api/v1/config/categories/{uuid.uuid4()}/fields",
        json={
            "fields": [
                {
                    "field_name": "test",
                    "display_name": "Test",
                }
            ]
        },
    )

    assert response.status_code == 404
