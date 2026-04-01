"""Run guard to prevent concurrent operations on the same document."""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


class RunGuard:
    """Prevents concurrent processing of the same resource.

    Uses asyncio locks per resource_id. Attempting to acquire
    a lock that's already held returns False (non-blocking).
    """

    def __init__(self) -> None:
        self._active: set[str] = set()
        self._lock = asyncio.Lock()

    async def acquire(self, resource_id: str) -> bool:
        """Try to acquire exclusive access. Returns False if already running."""
        async with self._lock:
            if resource_id in self._active:
                logger.warning("Concurrent operation rejected for resource %s", resource_id)
                return False
            self._active.add(resource_id)
            return True

    async def release(self, resource_id: str) -> None:
        """Release the guard for a resource."""
        async with self._lock:
            self._active.discard(resource_id)

    @property
    def active_count(self) -> int:
        """Number of currently active resources."""
        return len(self._active)
