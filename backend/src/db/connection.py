"""Async database connection layer with SQLAlchemy 2.0 and asyncpg.

Provides engine creation, session factory, and FastAPI dependency.
"""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)


def create_engine(
    database_url: str,
    pool_size: int = 5,
    max_overflow: int = 5,
) -> AsyncEngine:
    """Create an async SQLAlchemy engine with connection pooling.

    Args:
        database_url: PostgreSQL connection URL (postgresql+asyncpg://...).
        pool_size: Number of persistent connections in the pool.
        max_overflow: Max additional connections beyond pool_size.

    Returns:
        Configured async engine.
    """
    engine: AsyncEngine = create_async_engine(
        database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        echo=False,
    )
    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory bound to the given engine.

    Args:
        engine: The async SQLAlchemy engine.

    Returns:
        Configured async session maker.
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


# Module-level engine and session factory (initialized at startup)
_engine: "AsyncEngine | None" = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(
    database_url: str,
    pool_size: int = 5,
    max_overflow: int = 5,
) -> None:
    """Initialize the module-level engine and session factory."""
    global _engine, _session_factory
    masked = database_url.split("@")[-1] if "@" in database_url else database_url
    logger.info(
        "Initializing database engine -> %s (pool_size=%d, max_overflow=%d)",
        masked, pool_size, max_overflow,
    )
    _engine = create_engine(database_url, pool_size=pool_size, max_overflow=max_overflow)
    _session_factory = create_session_factory(_engine)


def get_engine() -> AsyncEngine:
    """Return the module-level engine. Raises if not initialized."""
    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call init_engine() first.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the module-level session factory. Raises if not initialized."""
    if _session_factory is None:
        raise RuntimeError("Session factory not initialized. Call init_engine() first.")
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    Commits on success, rolls back on exception.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            logger.warning("Session rollback triggered by unhandled exception")
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Dispose the module-level engine, closing all connections."""
    global _engine, _session_factory
    if _engine is not None:
        logger.info("Disposing database engine and connection pool")
        await _engine.dispose()
        _engine = None
        _session_factory = None
