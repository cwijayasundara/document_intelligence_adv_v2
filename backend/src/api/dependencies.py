"""Shared FastAPI dependencies for injection."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import AppSettings, get_settings
from src.db.connection import get_session as _get_session


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session. Commits on success, rolls back on error."""
    async for session in _get_session():
        yield session


def get_app_settings() -> AppSettings:
    """Return the cached application settings singleton."""
    return get_settings()
