"""Schema compatibility check against the upstream table layout.

Pins the column list and types so drift between our implementation and
``langgraph-checkpoint-postgres`` surfaces as a deliberate test update
rather than a silent data-format divergence.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from langgraph_checkpoint_asyncpg.migrations import apply_migrations

EXPECTED_CHECKPOINTS_COLUMNS = {
    "thread_id": "text",
    "checkpoint_ns": "text",
    "checkpoint_id": "text",
    "parent_checkpoint_id": "text",
    "type": "text",
    "checkpoint": "jsonb",
    "metadata": "jsonb",
}

EXPECTED_BLOBS_COLUMNS = {
    "thread_id": "text",
    "checkpoint_ns": "text",
    "channel": "text",
    "version": "text",
    "type": "text",
    "blob": "bytea",
}

EXPECTED_WRITES_COLUMNS = {
    "thread_id": "text",
    "checkpoint_ns": "text",
    "checkpoint_id": "text",
    "task_id": "text",
    "task_path": "text",
    "idx": "integer",
    "channel": "text",
    "type": "text",
    "blob": "bytea",
}


async def _columns(engine: AsyncEngine, table: str) -> dict[str, str]:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT column_name, data_type "
                "FROM information_schema.columns "
                "WHERE table_name = :t"
            ),
            {"t": table},
        )
        return {row[0]: row[1] for row in result.fetchall()}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("table", "expected"),
    [
        ("checkpoints", EXPECTED_CHECKPOINTS_COLUMNS),
        ("checkpoint_blobs", EXPECTED_BLOBS_COLUMNS),
        ("checkpoint_writes", EXPECTED_WRITES_COLUMNS),
    ],
)
async def test_columns_match_upstream(
    clean_engine: AsyncEngine, table: str, expected: dict[str, str]
) -> None:
    await apply_migrations(clean_engine)
    actual = await _columns(clean_engine, table)
    assert actual == expected, (
        f"schema drift for {table}: extra={set(actual) - set(expected)}, "
        f"missing={set(expected) - set(actual)}"
    )


@pytest.mark.asyncio
async def test_thread_id_indexes_exist(clean_engine: AsyncEngine) -> None:
    """Migrations v6-v8 create these indexes."""
    await apply_migrations(clean_engine)
    async with clean_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT indexname FROM pg_indexes WHERE schemaname = current_schema()")
        )
        indexes = {r[0] for r in result.fetchall()}
    assert "checkpoints_thread_id_idx" in indexes
    assert "checkpoint_blobs_thread_id_idx" in indexes
    assert "checkpoint_writes_thread_id_idx" in indexes
