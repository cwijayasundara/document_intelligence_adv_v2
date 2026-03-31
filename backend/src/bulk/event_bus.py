"""In-memory pub/sub event bus for pipeline progress."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class PipelineEventBus:
    """In-memory pub/sub for pipeline progress events."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, job_id: str) -> asyncio.Queue[dict[str, Any]]:
        """Subscribe to events for a job. Returns a queue to read from."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        async with self._lock:
            if job_id not in self._subscribers:
                self._subscribers[job_id] = []
            self._subscribers[job_id].append(queue)
        return queue

    async def unsubscribe(self, job_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Unsubscribe a queue from job events."""
        async with self._lock:
            if job_id in self._subscribers:
                self._subscribers[job_id] = [q for q in self._subscribers[job_id] if q is not queue]
                if not self._subscribers[job_id]:
                    del self._subscribers[job_id]

    async def publish(self, job_id: str, event: dict[str, Any]) -> None:
        """Publish an event to all subscribers of a job."""
        async with self._lock:
            queues = list(self._subscribers.get(job_id, []))
        for queue in queues:
            await queue.put(event)

    @property
    def subscriber_count(self) -> int:
        """Total number of active subscriptions."""
        return sum(len(qs) for qs in self._subscribers.values())
