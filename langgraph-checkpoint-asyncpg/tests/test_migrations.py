"""Migration runner tests against a real PostgreSQL."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from langgraph_checkpoint_asyncpg.migrations import apply_migrations
from langgraph_checkpoint_asyncpg.sql import LATEST_VERSION


async def _current_version(engine: AsyncEngine) -> int:
    async with engine.connect() as conn:
        row = await conn.execute(text("SELECT COALESCE(MAX(v), -1) FROM checkpoint_migrations"))
        return int(row.scalar_one())


async def _table_names(engine: AsyncEngine) -> set[str]:
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = current_schema()")
        )
        return {r[0] for r in result.fetchall()}


@pytest.mark.asyncio
async def test_cold_start_applies_all_versions(clean_engine: AsyncEngine) -> None:
    await apply_migrations(clean_engine)

    assert await _current_version(clean_engine) == LATEST_VERSION
    tables = await _table_names(clean_engine)
    assert {
        "checkpoints",
        "checkpoint_blobs",
        "checkpoint_writes",
        "checkpoint_migrations",
    } <= tables


@pytest.mark.asyncio
async def test_rerun_is_idempotent(clean_engine: AsyncEngine) -> None:
    await apply_migrations(clean_engine)
    await apply_migrations(clean_engine)
    await apply_migrations(clean_engine)
    assert await _current_version(clean_engine) == LATEST_VERSION


@pytest.mark.asyncio
async def test_resumes_from_partial_state(clean_engine: AsyncEngine) -> None:
    # Simulate a database left at an earlier schema version.
    await apply_migrations(clean_engine)
    async with clean_engine.begin() as conn:
        await conn.execute(text("DELETE FROM checkpoint_migrations WHERE v > 5"))
    assert await _current_version(clean_engine) == 5

    await apply_migrations(clean_engine)
    assert await _current_version(clean_engine) == LATEST_VERSION


@pytest.mark.asyncio
async def test_task_path_column_exists(clean_engine: AsyncEngine) -> None:
    """Migration v9 adds checkpoint_writes.task_path."""
    await apply_migrations(clean_engine)
    async with clean_engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'checkpoint_writes'"
            )
        )
        columns = {r[0] for r in result.fetchall()}
    assert "task_path" in columns
