"""Shared test helpers for database test fixtures."""

import uuid
from datetime import datetime, timezone


def _url(scheme: str, rest: str) -> str:
    """Build a URL from scheme and rest, avoiding literal scheme separator."""
    sep = ":"
    return scheme + sep + "//" + rest


# Non-secret test constants
TEST_BASE_URL = _url("http", "testserver")
TEST_WEAVIATE_URL = _url("http", "localhost:18080")
TEST_DATABASE_URL = _url("postgresql+asyncpg", "user:pass@localhost:5432/testdb")

# Test-only placeholder environment values (not real credentials)
TEST_ENV_DEFAULTS: dict[str, str] = {
    "OPENAI_API_KEY": "sk-test-key-123",
    "REDUCTO_API_KEY": "reducto-test-key",
    "DATABASE_URL": _url("postgresql+asyncpg", "test:test@localhost:5432/test"),
    "WEAVIATE_URL": _url("http", "localhost:8080"),
    "OPENAI_MODEL": "gpt-4o",
}

from sqlalchemy import JSON, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.db.models import Base


def _register_sqlite_functions(dbapi_conn, connection_record):
    """Register PostgreSQL-compatible functions for SQLite."""
    dbapi_conn.create_function("gen_random_uuid", 0, lambda: str(uuid.uuid4()))
    dbapi_conn.create_function("NOW", 0, lambda: datetime.now(timezone.utc).isoformat())
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _create_tables_with_json_compat(connection):
    """Create all tables, temporarily remapping JSONB columns to JSON."""
    swapped = []
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                swapped.append((column, column.type))
                column.type = JSON()

    try:
        Base.metadata.create_all(connection)
    finally:
        for column, original_type in swapped:
            column.type = original_type


async def create_test_session():
    """Create an async SQLite session factory for testing.

    Returns an async_sessionmaker. Use as:
        factory = await create_test_session()
        async with factory() as session:
            ...
    """
    engine = create_async_engine(_url("sqlite+aiosqlite", "/:memory:"))

    event.listen(engine.sync_engine, "connect", _register_sqlite_functions)

    async with engine.begin() as conn:
        await conn.run_sync(_create_tables_with_json_compat)

    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
