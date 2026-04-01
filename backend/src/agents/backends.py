"""In-memory backend replacing FilesystemBackend for stateless deployments."""

from __future__ import annotations

from typing import Any


class InMemoryBackend:
    """In-memory state backend for agent orchestration.

    Replaces FilesystemBackend to avoid filesystem dependencies
    in containerized/serverless deployments.
    """

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    async def read(self, key: str) -> Any:
        """Read a value by key. Returns None if not found."""
        return self._store.get(key)

    async def write(self, key: str, data: Any) -> None:
        """Write a value by key."""
        self._store[key] = data

    async def delete(self, key: str) -> bool:
        """Delete a value by key. Returns True if existed."""
        return self._store.pop(key, None) is not None

    def clear(self) -> None:
        """Clear all stored data."""
        self._store.clear()
