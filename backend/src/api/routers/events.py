"""SSE endpoint for real-time system events."""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.api.shutdown import get_shutdown_event
from src.audit.queue import subscribe_sse, unsubscribe_sse

logger = logging.getLogger(__name__)

router = APIRouter()


async def _event_stream() -> AsyncGenerator[str, None]:
    """Yield SSE-formatted audit events, closing cleanly on app shutdown.

    The loop races queue.get() against the lifespan shutdown event so the
    generator returns promptly during uvicorn graceful shutdown (including
    `--reload`), instead of blocking the server until the client disconnects.
    """
    q = subscribe_sse()
    shutdown = get_shutdown_event()
    try:
        while not shutdown.is_set():
            get_task = asyncio.create_task(q.get())
            shutdown_task = asyncio.create_task(shutdown.wait())
            try:
                done, pending = await asyncio.wait(
                    {get_task, shutdown_task},
                    timeout=30.0,
                    return_when=asyncio.FIRST_COMPLETED,
                )
            finally:
                for t in (get_task, shutdown_task):
                    if not t.done():
                        t.cancel()

            if shutdown_task in done:
                return
            if get_task in done:
                event = get_task.result()
                yield f"data: {json.dumps(event)}\n\n"
                continue
            # Neither fired — 30s timeout. Emit keepalive and re-enter loop.
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
