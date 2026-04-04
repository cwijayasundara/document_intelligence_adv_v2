"""SSE endpoint for real-time system events."""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.audit.queue import subscribe_sse, unsubscribe_sse

logger = logging.getLogger(__name__)

router = APIRouter()


async def _event_stream() -> AsyncGenerator[str, None]:
    """Yield SSE-formatted audit events as they happen."""
    q = subscribe_sse()
    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=30.0)
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
    finally:
        unsubscribe_sse(q)


@router.get("/events/stream", summary="Real-time system events via SSE")
async def stream_events() -> StreamingResponse:
    """Stream all audit events in real-time via Server-Sent Events."""
    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
