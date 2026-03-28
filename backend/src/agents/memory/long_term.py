"""PostgreSQL-backed long-term memory for agent conversations.

Provides persistent storage for conversation summaries and a
generic key-value store with retry logic for transient DB errors.
"""

import asyncio
import functools
import logging
from typing import Any, Callable, ParamSpec, TypeVar

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.memory import (
    ConversationSummaryRepository,
    MemoryEntryRepository,
)

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")

MAX_RETRIES = 3
RETRY_BASE_DELAY = 0.5


def retry_on_db_error(
    func: Callable[P, T],
) -> Callable[P, T]:
    """Decorator that retries async functions on transient DB errors."""

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                return await func(*args, **kwargs)  # type: ignore[misc]
            except OperationalError as exc:
                last_exc = exc
                delay = RETRY_BASE_DELAY * (2**attempt)
                logger.warning(
                    "DB transient error (attempt %d/%d): %s. "
                    "Retrying in %.1fs...",
                    attempt + 1,
                    MAX_RETRIES,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
        raise last_exc  # type: ignore[misc]

    return wrapper  # type: ignore[return-value]


class PostgresLongTermMemory:
    """Persistent memory backed by PostgreSQL.

    Stores conversation summaries and generic key-value data.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._summary_repo = ConversationSummaryRepository(session)
        self._memory_repo = MemoryEntryRepository(session)

    @retry_on_db_error
    async def save_conversation_summary(
        self,
        session_id: str,
        agent_type: str,
        summary: str,
        key_topics: list[str] | None = None,
        documents_discussed: list[str] | None = None,
        queries_count: int = 0,
    ) -> dict[str, Any]:
        """Save or update a conversation summary with upsert semantics."""
        record = await self._summary_repo.upsert(
            session_id=session_id,
            agent_type=agent_type,
            summary=summary,
            key_topics=key_topics or [],
            documents_discussed=documents_discussed or [],
            queries_count=queries_count,
        )
        return {
            "session_id": record.session_id,
            "agent_type": record.agent_type,
            "summary": record.summary,
            "key_topics": record.key_topics,
            "documents_discussed": record.documents_discussed,
            "queries_count": record.queries_count,
        }

    @retry_on_db_error
    async def get_conversation_summary(
        self, session_id: str
    ) -> dict[str, Any] | None:
        """Retrieve a conversation summary by session ID."""
        record = await self._summary_repo.get_by_session(session_id)
        if record is None:
            return None
        return {
            "session_id": record.session_id,
            "agent_type": record.agent_type,
            "summary": record.summary,
            "key_topics": record.key_topics,
            "documents_discussed": record.documents_discussed,
            "queries_count": record.queries_count,
        }

    @retry_on_db_error
    async def put(
        self, namespace: str, key: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Store a key-value entry in the given namespace."""
        entry = await self._memory_repo.put(namespace, key, data)
        return {
            "namespace": entry.namespace,
            "key": entry.key,
            "data": entry.data,
        }

    @retry_on_db_error
    async def get(
        self, namespace: str, key: str
    ) -> dict[str, Any] | None:
        """Retrieve a value by namespace and key."""
        entry = await self._memory_repo.get(namespace, key)
        if entry is None:
            return None
        return {
            "namespace": entry.namespace,
            "key": entry.key,
            "data": entry.data,
        }

    @retry_on_db_error
    async def delete(self, namespace: str, key: str) -> bool:
        """Delete a key-value entry. Returns True if deleted."""
        return await self._memory_repo.delete(namespace, key)

    @retry_on_db_error
    async def search(self, namespace: str) -> list[dict[str, Any]]:
        """List all entries in a namespace."""
        entries = await self._memory_repo.search(namespace)
        return [
            {
                "namespace": e.namespace,
                "key": e.key,
                "data": e.data,
            }
            for e in entries
        ]
