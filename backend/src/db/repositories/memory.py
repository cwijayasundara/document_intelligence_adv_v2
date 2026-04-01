"""Repositories for conversation summaries and memory entries."""

import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import ConversationSummary, MemoryEntry


class ConversationSummaryRepository:
    """Async repository for conversation summary CRUD."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self,
        session_id: str,
        agent_type: str,
        summary: str,
        key_topics: list[str],
        documents_discussed: list[str],
        queries_count: int,
        user_id: str | None = None,
    ) -> ConversationSummary:
        """Create or update a conversation summary (upsert by session_id)."""
        stmt = select(ConversationSummary).where(ConversationSummary.session_id == session_id)
        if user_id is not None:
            stmt = stmt.where(ConversationSummary.user_id == user_id)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            existing.agent_type = agent_type
            existing.summary = summary
            existing.key_topics = key_topics
            existing.documents_discussed = documents_discussed
            existing.queries_count = queries_count
            await self._session.flush()
            return existing

        record = ConversationSummary(
            id=uuid.uuid4(),
            session_id=session_id,
            agent_type=agent_type,
            summary=summary,
            key_topics=key_topics,
            documents_discussed=documents_discussed,
            queries_count=queries_count,
            user_id=user_id,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_by_session(
        self,
        session_id: str,
        user_id: str | None = None,
    ) -> ConversationSummary | None:
        """Get a conversation summary by session ID."""
        stmt = select(ConversationSummary).where(ConversationSummary.session_id == session_id)
        if user_id is not None:
            stmt = stmt.where(ConversationSummary.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


class MemoryEntryRepository:
    """Async repository for generic key-value memory entries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def put(self, namespace: str, key: str, data: dict[str, Any]) -> MemoryEntry:
        """Create or update a memory entry (upsert by namespace+key)."""
        stmt = select(MemoryEntry).where(
            MemoryEntry.namespace == namespace,
            MemoryEntry.key == key,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            existing.data = data
            await self._session.flush()
            return existing

        entry = MemoryEntry(
            id=uuid.uuid4(),
            namespace=namespace,
            key=key,
            data=data,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def get(self, namespace: str, key: str) -> MemoryEntry | None:
        """Get a memory entry by namespace and key."""
        stmt = select(MemoryEntry).where(
            MemoryEntry.namespace == namespace,
            MemoryEntry.key == key,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, namespace: str, key: str) -> bool:
        """Delete a memory entry. Returns True if deleted."""
        stmt = delete(MemoryEntry).where(
            MemoryEntry.namespace == namespace,
            MemoryEntry.key == key,
        )
        result = await self._session.execute(stmt)
        return (result.rowcount or 0) > 0

    async def search(self, namespace: str) -> list[MemoryEntry]:
        """List all entries in a namespace."""
        stmt = (
            select(MemoryEntry)
            .where(MemoryEntry.namespace == namespace)
            .order_by(MemoryEntry.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
