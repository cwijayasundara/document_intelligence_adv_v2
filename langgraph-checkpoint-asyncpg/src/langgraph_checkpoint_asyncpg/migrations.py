"""Idempotent schema migrations for the asyncpg-backed checkpointer.

Mirrors the nine-version migration chain used by
``langgraph-checkpoint-postgres``. Index-creation statements that require
``CREATE INDEX CONCURRENTLY`` are executed in AUTOCOMMIT mode because
CONCURRENTLY cannot run inside a transaction block.
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from .sql import (
    INSERT_MIGRATION_VERSION_SQL,
    MIGRATIONS,
    SELECT_MAX_MIGRATION_VERSION_SQL,
)

logger = logging.getLogger(__name__)


async def apply_migrations(engine: AsyncEngine) -> None:
    """Advance the checkpointer schema to the latest known version.

    Idempotent: safe to call on every process startup. Partial progress is
    durable because each applied migration records its version before the
    next one runs.
    """
    await _ensure_migrations_table(engine)
    current = await _current_version(engine)

    for migration in MIGRATIONS:
        if migration.version <= current:
            continue

        logger.info(
            "Applying checkpointer migration v%d (concurrent=%s)",
            migration.version,
            migration.concurrent,
        )
        if migration.concurrent:
            await _apply_concurrent(engine, migration.version, migration.statement)
        else:
            await _apply_transactional(engine, migration.version, migration.statement)


async def _ensure_migrations_table(engine: AsyncEngine) -> None:
    """Create the version-tracking table if it doesn't exist (migration v0)."""
    bootstrap = MIGRATIONS[0]
    async with engine.begin() as conn:
        await conn.execute(text(bootstrap.statement))


async def _current_version(engine: AsyncEngine) -> int:
    async with engine.connect() as conn:
        result = await conn.execute(SELECT_MAX_MIGRATION_VERSION_SQL)
        return int(result.scalar_one())


async def _apply_transactional(engine: AsyncEngine, version: int, statement: str) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(statement))
        await conn.execute(INSERT_MIGRATION_VERSION_SQL, {"v": version})


async def _apply_concurrent(engine: AsyncEngine, version: int, statement: str) -> None:
    # CREATE INDEX CONCURRENTLY must not run in a transaction block.
    autocommit_engine = engine.execution_options(isolation_level="AUTOCOMMIT")
    async with autocommit_engine.connect() as conn:
        await conn.execute(text(statement))
    # Record the version in its own small transaction. A crash between the
    # two steps is safe: the DDL used IF NOT EXISTS, so a rerun reapplies
    # the bump without duplicating the index.
    async with engine.begin() as conn:
        await conn.execute(INSERT_MIGRATION_VERSION_SQL, {"v": version})
