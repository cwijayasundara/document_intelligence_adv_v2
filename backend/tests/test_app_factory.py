"""Tests for FastAPI app factory and category seeding."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.app import _seed_default_category, create_app


def test_create_app_returns_fastapi() -> None:
    """create_app returns a FastAPI instance."""
    app = create_app(database_url="")
    assert isinstance(app, FastAPI)


def test_create_app_has_routes() -> None:
    """App includes health, documents, and config routers."""
    app = create_app(database_url="")
    route_paths = [r.path for r in app.routes if hasattr(r, "path")]
    assert "/api/v1/health" in route_paths
    assert "/api/v1/documents/upload" in route_paths
    assert "/api/v1/config/categories" in route_paths


@patch("src.db.repositories.categories.CategoryRepository.create", new_callable=AsyncMock)
@patch("src.db.repositories.categories.CategoryRepository.count", new_callable=AsyncMock)
@patch("src.api.app.get_session_factory")
async def test_seed_default_category_creates_when_empty(
    mock_factory: MagicMock,
    mock_count: AsyncMock,
    mock_create: AsyncMock,
) -> None:
    """_seed_default_category creates category when none exist."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()
    mock_factory.return_value = MagicMock(return_value=mock_session)
    mock_count.return_value = 0

    await _seed_default_category()

    mock_create.assert_called_once()


@patch("src.db.repositories.categories.CategoryRepository.create", new_callable=AsyncMock)
@patch("src.db.repositories.categories.CategoryRepository.count", new_callable=AsyncMock)
@patch("src.api.app.get_session_factory")
async def test_seed_default_category_skips_when_exists(
    mock_factory: MagicMock,
    mock_count: AsyncMock,
    mock_create: AsyncMock,
) -> None:
    """_seed_default_category does nothing when categories exist."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_factory.return_value = MagicMock(return_value=mock_session)
    mock_count.return_value = 3

    await _seed_default_category()

    mock_create.assert_not_called()


@patch("src.api.app.get_session_factory")
async def test_seed_default_category_handles_db_error(
    mock_factory: MagicMock,
) -> None:
    """_seed_default_category handles exceptions gracefully."""
    mock_factory.side_effect = RuntimeError("DB not ready")
    # Should not raise
    await _seed_default_category()
