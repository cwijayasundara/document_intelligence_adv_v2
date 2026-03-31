"""SSE streaming endpoint for pipeline progress."""

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.api.dependencies import get_current_user_id
from src.bulk.event_bus import PipelineEventBus

logger = logging.getLogger(__name__)

router = APIRouter()

_event_bus: PipelineEventBus | None = None


def get_event_bus() -> PipelineEventBus:
    """Return the singleton event bus."""
    global _event_bus  # noqa: PLW0603
    if _event_bus is None:
        _event_bus = PipelineEventBus()
    return _event_bus


async def _sse_generator(
    job_id: str,
    event_bus: PipelineEventBus,
) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE-formatted events."""
    queue = await event_bus.subscribe(job_id)
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") == "job_completed":
                    break
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
    finally:
        await event_bus.unsubscribe(job_id, queue)


@router.get("/stream/jobs/{job_id}", summary="Stream pipeline progress")
async def stream_job_progress(
    job_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
) -> StreamingResponse:
    """Stream pipeline progress events via SSE."""
    event_bus = get_event_bus()
    return StreamingResponse(
        _sse_generator(str(job_id), event_bus),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
