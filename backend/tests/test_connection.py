"""Tests for E1-S3: Database Connection & Migrations.

Verifies async engine creation, session factory, connection pooling,
and get_session dependency.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.db.connection import (
    create_engine,
    create_session_factory,
    get_engine,
    get_session,
    get_session_factory,
    init_engine,
    dispose_engine,
)
import src.db.connection as conn_module


class TestCreateEngine:
    """Test async engine creation."""

    def test_creates_async_engine(self) -> None:
        engine = create_engine(
            "postgresql+asyncpg://test:test@localhost:5432/test"
        )
        assert isinstance(engine, AsyncEngine)

    def test_engine_pool_size(self) -> None:
        engine = create_engine(
            "postgresql+asyncpg://test:test@localhost:5432/test"
        )
        assert engine.pool.size() == 5

    def test_engine_max_overflow(self) -> None:
        engine = create_engine(
            "postgresql+asyncpg://test:test@localhost:5432/test"
        )
        assert engine.pool._max_overflow == 10

    def test_engine_url_contains_asyncpg(self) -> None:
        engine = create_engine(
            "postgresql+asyncpg://test:test@localhost:5432/test"
        )
        assert "asyncpg" in str(engine.url)


class TestCreateSessionFactory:
    """Test session factory creation."""

    def test_creates_session_factory(self) -> None:
        engine = create_engine(
            "postgresql+asyncpg://test:test@localhost:5432/test"
        )
        factory = create_session_factory(engine)
        assert isinstance(factory, async_sessionmaker)

    def test_factory_produces_async_sessions(self) -> None:
        engine = create_engine(
            "postgresql+asyncpg://test:test@localhost:5432/test"
        )
        factory = create_session_factory(engine)
        # The factory class should create AsyncSession instances
        assert factory.class_ is AsyncSession


class TestModuleLevelInitialization:
    """Test init_engine, get_engine, get_session_factory module-level functions."""

    def setup_method(self) -> None:
        """Reset module state before each test."""
        conn_module._engine = None
        conn_module._session_factory = None

    def test_get_engine_raises_before_init(self) -> None:
        with pytest.raises(RuntimeError, match="Database engine not initialized"):
            get_engine()

    def test_get_session_factory_raises_before_init(self) -> None:
        with pytest.raises(RuntimeError, match="Session factory not initialized"):
            get_session_factory()

    def test_init_engine_sets_engine(self) -> None:
        init_engine("postgresql+asyncpg://test:test@localhost:5432/test")
        engine = get_engine()
        assert isinstance(engine, AsyncEngine)

    def test_init_engine_sets_session_factory(self) -> None:
        init_engine("postgresql+asyncpg://test:test@localhost:5432/test")
        factory = get_session_factory()
        assert isinstance(factory, async_sessionmaker)

    async def test_dispose_engine(self) -> None:
        init_engine("postgresql+asyncpg://test:test@localhost:5432/test")
        assert conn_module._engine is not None
        await dispose_engine()
        assert conn_module._engine is None
        assert conn_module._session_factory is None


class TestGetSessionDependency:
    """Test get_session async generator."""

    async def test_get_session_raises_when_not_initialized(self) -> None:
        conn_module._engine = None
        conn_module._session_factory = None
        with pytest.raises(RuntimeError):
            async for _ in get_session():
                pass

    async def test_get_session_yields_session_when_initialized(self) -> None:
        init_engine("postgresql+asyncpg://test:test@localhost:5432/test")
        # We can verify the generator yields something; actual DB ops
        # would require a running database. We mock the session.
        mock_session = AsyncMock(spec=AsyncSession)
        mock_factory = MagicMock(spec=async_sessionmaker)

        # Create a proper async context manager
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = mock_cm

        conn_module._session_factory = mock_factory
        async for session in get_session():
            assert session is mock_session
