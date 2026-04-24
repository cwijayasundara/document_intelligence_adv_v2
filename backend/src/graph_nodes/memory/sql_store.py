"""SQLAlchemy-backed LangGraph Store.

Persists agent long-term memory to the existing `memory_entries` table so
corrections written by the API server survive across processes (harvest CLI,
eval runs, restarts).

Deliberately implements only the subset used by this codebase — aput / aget /
asearch. LangGraph's full `BaseStore` contract (batch/abatch, list_namespaces,
etc.) is not needed here; callers go through the thin `save_correction` /
`load_corrections` helpers in `store.py`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from langgraph.store.base import Item, SearchItem
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models.memory import MemoryEntry

# The ORM model declares a `user_id` column that the live `memory_entries`
# table does not have (migration drift). Select only the columns we know
# exist in the DB so queries don't fail on UndefinedColumnError.
_COLS = (
    MemoryEntry.namespace,
    MemoryEntry.key,
    MemoryEntry.data,
    MemoryEntry.created_at,
    MemoryEntry.updated_at,
)

logger = logging.getLogger(__name__)

# ASCII Record Separator — joins tuple namespaces into the single varchar
# column. Not a character that appears in any realistic namespace segment.
_NS_SEP = "\x1e"


def _encode_ns(namespace: tuple[str, ...]) -> str:
    return _NS_SEP.join(namespace)


def _decode_ns(stored: str) -> tuple[str, ...]:
    return tuple(stored.split(_NS_SEP)) if stored else ()


def _to_utc(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class SqlAlchemyMemoryStore:
    """Minimal async Store backed by the `memory_entries` table."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def aput(
        self,
        namespace: tuple[str, ...],
        key: str,
        value: dict[str, Any],
        index: Any = None,
        *,
        ttl: Any = None,
    ) -> None:
        """Upsert a value at (namespace, key)."""
        stmt = pg_insert(MemoryEntry).values(
            namespace=_encode_ns(namespace),
            key=key,
            data=value,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_memory_entries_ns_key",
            set_={"data": stmt.excluded.data, "updated_at": text("NOW()")},
        )
        async with self._factory() as session:
            await session.execute(stmt)
            await session.commit()

    async def aget(
        self,
        namespace: tuple[str, ...],
        key: str,
        *,
        refresh_ttl: Any = None,
    ) -> Item | None:
        """Return the Item at (namespace, key), or None."""
        stmt = select(*_COLS).where(
            MemoryEntry.namespace == _encode_ns(namespace),
            MemoryEntry.key == key,
        )
        async with self._factory() as session:
            row = (await session.execute(stmt)).first()
        if row is None:
            return None
        ns, row_key, data, created_at, updated_at = row
        return Item(
            value=dict(data or {}),
            key=row_key,
            namespace=_decode_ns(ns),
            created_at=_to_utc(created_at),
            updated_at=_to_utc(updated_at),
        )

    async def asearch(
        self,
        namespace_prefix: tuple[str, ...],
        *,
        query: Any = None,
        filter: Any = None,  # noqa: A002 — match BaseStore kwarg name.
        limit: int = 10,
        offset: int = 0,
        refresh_ttl: Any = None,
    ) -> list[SearchItem]:
        """Scan rows whose namespace has `namespace_prefix` as a prefix.

        Semantic search (`query=...`) is not supported — the underlying table
        has no vector column. Callers that need it should use an embedding-aware
        store. Filters on JSONB `data` are not wired up yet either.
        """
        if query is not None or filter is not None:
            logger.warning(
                "SqlAlchemyMemoryStore.asearch ignores query/filter; namespace prefix only."
            )

        stmt = select(*_COLS).order_by(MemoryEntry.updated_at.desc())
        if namespace_prefix:
            prefix = _encode_ns(namespace_prefix)
            # Escape LIKE wildcards in the literal prefix.
            escaped = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            like_pattern = escaped + _NS_SEP + "%"
            stmt = stmt.where(
                (MemoryEntry.namespace == prefix)
                | MemoryEntry.namespace.like(like_pattern, escape="\\")
            )
        stmt = stmt.limit(limit).offset(offset)

        async with self._factory() as session:
            rows = (await session.execute(stmt)).all()

        return [
            SearchItem(
                value=dict(data or {}),
                key=row_key,
                namespace=_decode_ns(ns),
                created_at=_to_utc(created_at),
                updated_at=_to_utc(updated_at),
            )
            for ns, row_key, data, created_at, updated_at in rows
        ]
