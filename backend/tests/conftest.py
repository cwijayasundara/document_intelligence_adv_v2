"""Shared test fixtures for the backend test suite."""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

try:
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from src.api.app import create_app
    from tests.db_helpers import TEST_BASE_URL, TEST_ENV_DEFAULTS

    _APP_AVAILABLE = True
except ImportError:
    _APP_AVAILABLE = False


@pytest.fixture
def test_env(tmp_path: Path) -> dict[str, str]:
    """Provide a complete set of test environment variables."""
    env_file = tmp_path / ".env"
    lines = [f"{k}={v}" for k, v in TEST_ENV_DEFAULTS.items()]
    env_file.write_text("\n".join(lines) + "\n")
    return {**TEST_ENV_DEFAULTS, "env_file": str(env_file)}


@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI test app without database initialization."""
    return create_app(database_url="")


@pytest.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=TEST_BASE_URL) as ac:
        yield ac
