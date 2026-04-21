"""Shared test fixtures.

Uses testcontainers to start an ephemeral PostgreSQL 16 instance per test
session. Skips the entire module if Docker is unavailable so CI and local
runs without a Docker daemon degrade gracefully instead of failing hard.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

try:
    from testcontainers.postgres import PostgresContainer
except ImportError:  # pragma: no cover
    PostgresContainer = None  # type: ignore[assignment,misc]

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


@pytest.fixture(scope="session")
def postgres_container() -> Any:
    if PostgresContainer is None:
        pytest.skip("testcontainers not installed")
    try:
        container = PostgresContainer("postgres:16-alpine")
        container.start()
    except Exception as exc:  # docker unavailable, permission denied, etc.
        pytest.skip(f"could not start postgres container: {exc}")
    try:
        yield container
    finally:
        container.stop()


@pytest.fixture(scope="session")
def async_dsn(postgres_container: Any) -> str:
    sync_url = postgres_container.get_connection_url()
    # testcontainers returns postgresql+psycopg2://... — swap the driver.
    return sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)


@pytest.fixture
async def engine(async_dsn: str) -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(async_dsn)
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest.fixture
async def clean_engine(engine: AsyncEngine) -> AsyncIterator[AsyncEngine]:
    """Engine whose checkpointer tables are dropped before each test."""
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "DROP TABLE IF EXISTS "
                "checkpoint_writes, checkpoint_blobs, checkpoints, checkpoint_migrations "
                "CASCADE"
            )
        )
    yield engine
