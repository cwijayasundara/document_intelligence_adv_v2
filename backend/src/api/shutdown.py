"""Per-loop shutdown signal shared by the app lifespan and long-lived handlers.

Long-running endpoints (SSE streams, websocket loops) should race their work
against `get_shutdown_event().wait()` so they exit promptly when uvicorn is
winding the server down. Without this, `--reload` and graceful shutdown block
until every client disconnects.
"""

from __future__ import annotations

import asyncio

_shutdown_event: asyncio.Event | None = None


def get_shutdown_event() -> asyncio.Event:
    """Return the per-process shutdown Event, creating it on first access."""
    global _shutdown_event
    if _shutdown_event is None:
        _shutdown_event = asyncio.Event()
    return _shutdown_event


def trigger_shutdown() -> None:
    """Set the shutdown event. Safe to call repeatedly."""
    get_shutdown_event().set()


def reset_shutdown() -> None:
    """Clear the shutdown event. Used by tests that spin up a fresh app."""
    get_shutdown_event().clear()
