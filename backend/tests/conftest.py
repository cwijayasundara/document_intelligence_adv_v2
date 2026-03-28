"""Shared test fixtures for the backend test suite."""

import os
from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app
from src.db.connection import (
    _engine,
    _session_factory,
    create_engine,
    create_session_factory,
)


@pytest.fixture
def test_env(tmp_path: Path) -> dict[str, str]:
    """Provide a complete set of test environment variables."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "OPENAI_API_KEY=sk-test-key-123\n"
        "REDUCTO_API_KEY=reducto-test-key\n"
        "DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/test\n"
        "WEAVIATE_URL=http://localhost:8080\n"
        "OPENAI_MODEL=gpt-4o\n"
    )
    return {
        "OPENAI_API_KEY": "sk-test-key-123",
        "REDUCTO_API_KEY": "reducto-test-key",
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
        "WEAVIATE_URL": "http://localhost:8080",
        "OPENAI_MODEL": "gpt-4o",
        "env_file": str(env_file),
    }


@pytest.fixture
def app() -> "FastAPI":
    """Create a FastAPI test app without database initialization."""
    return create_app(database_url="")


@pytest.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
