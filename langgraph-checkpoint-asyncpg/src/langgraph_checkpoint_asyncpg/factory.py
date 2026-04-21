"""Factory helper for constructing an ``AsyncpgCheckpointSaver``."""

from __future__ import annotations

from langgraph.checkpoint.base import SerializerProtocol
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from .saver import AsyncpgCheckpointSaver


async def create_checkpointer(
    engine_or_dsn: AsyncEngine | str,
    *,
    auto_setup: bool = True,
    serde: SerializerProtocol | None = None,
) -> AsyncpgCheckpointSaver:
    """Build an ``AsyncpgCheckpointSaver`` and optionally run ``setup()``.

    Parameters
    ----------
    engine_or_dsn:
        Either an existing ``AsyncEngine`` (recommended — share the app's
        pool) or a ``postgresql+asyncpg://`` DSN string. When given a DSN,
        the function creates and owns a new engine.
    auto_setup:
        If ``True`` (default), ``setup()`` is awaited before the saver is
        returned. Pass ``False`` to defer schema setup.
    serde:
        Optional serializer override. Defaults to ``JsonPlusSerializer``.
    """
    engine = create_async_engine(engine_or_dsn) if isinstance(engine_or_dsn, str) else engine_or_dsn

    saver = AsyncpgCheckpointSaver(engine, serde=serde)
    if auto_setup:
        await saver.setup()
    return saver
