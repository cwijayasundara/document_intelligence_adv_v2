"""Shared FastAPI dependencies for injection."""

from collections.abc import AsyncGenerator

from fastapi import Header, HTTPException
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


async def get_current_user_id(
    x_user_id: str | None = Header(None, alias="X-User-Id"),
) -> str:
    """Extract and validate the X-User-Id header."""
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(status_code=401, detail="X-User-Id header required")
    return x_user_id.strip()
