"""LangGraph Store integration for long-term agent memory.

Provides a PostgreSQL-backed Store with semantic search for
classification corrections, extraction patterns, and user preferences.
Falls back to InMemoryStore when no database is available.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Memory namespaces
NS_CLASSIFICATION_CORRECTIONS = "classification_corrections"
NS_CLASSIFICATION_PATTERNS = "classification_patterns"
NS_EXTRACTION_CORRECTIONS = "extraction_corrections"
NS_EXTRACTION_PATTERNS = "extraction_patterns"
NS_RAG_QUERY_PATTERNS = "rag_query_patterns"
NS_USER_PREFERENCES = "user_preferences"

_store: Any | None = None


async def get_memory_store() -> Any:
    """Get or create the LangGraph memory store.

    Prefers a PostgreSQL-backed Store (via the existing `memory_entries`
    table) so corrections persist across processes. Falls back to
    `InMemoryStore` only when the database is unreachable.
    """
    global _store
    if _store is not None:
        return _store

    sql_store = await _try_build_sql_store()
    if sql_store is not None:
        _store = sql_store
        logger.info("Using SQL-backed agent memory (memory_entries table)")
        return _store

    try:
        from langgraph.store.memory import InMemoryStore

        _store = InMemoryStore()
        logger.warning(
            "Falling back to InMemoryStore for agent memory — corrections will "
            "not persist across processes."
        )
    except Exception as exc:
        logger.warning("Could not create memory store: %s", exc)
        _store = _create_dict_store()

    return _store


async def _try_build_sql_store() -> Any | None:
    """Build a SqlAlchemyMemoryStore if the database is reachable."""
    try:
        from sqlalchemy import text

        from src.config.settings import get_settings
        from src.db.connection import get_session_factory, init_engine
        from src.graph_nodes.memory.sql_store import SqlAlchemyMemoryStore

        settings = get_settings()
        init_engine(settings.database_url, pool_size=2, max_overflow=1)
        factory = get_session_factory()
        # Probe the connection so we fail fast when the DB is down.
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        return SqlAlchemyMemoryStore(factory)
    except Exception as exc:  # noqa: BLE001 — surface as a downgrade to InMemory.
        logger.warning("SQL-backed memory store unavailable (%s)", exc)
        return None


def _create_dict_store() -> Any:
    """Minimal dict-based store fallback."""

    class DictStore:
        def __init__(self) -> None:
            self._data: dict[tuple, dict[str, Any]] = {}

        async def aput(
            self,
            namespace: tuple[str, ...],
            key: str,
            value: dict[str, Any],
        ) -> None:
            self._data[(namespace, key)] = value

        async def aget(
            self,
            namespace: tuple[str, ...],
            key: str,
        ) -> dict[str, Any] | None:
            return self._data.get((namespace, key))

        async def asearch(
            self,
            namespace: tuple[str, ...],
            *,
            limit: int = 10,
        ) -> list[dict[str, Any]]:
            results = []
            for (ns, _key), val in self._data.items():
                if ns == namespace:
                    results.append(val)
                    if len(results) >= limit:
                        break
            return results

    return DictStore()


async def save_correction(
    user_id: str,
    correction_type: str,
    key: str,
    data: dict[str, Any],
) -> None:
    """Save a user correction to long-term memory.

    Args:
        user_id: User who made the correction.
        correction_type: 'classification' or 'extraction'.
        key: Unique key for this correction.
        data: Correction data to store.
    """
    store = await get_memory_store()
    ns_map = {
        "classification": NS_CLASSIFICATION_CORRECTIONS,
        "extraction": NS_EXTRACTION_CORRECTIONS,
    }
    namespace = (ns_map.get(correction_type, correction_type), user_id)

    await store.aput(namespace, key, {"user_id": user_id, **data})
    logger.info(
        "Saved %s correction for user %s: key=%s",
        correction_type,
        user_id,
        key,
    )


async def load_corrections(
    user_id: str,
    correction_type: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Load corrections from long-term memory for a single user.

    Args:
        user_id: User whose corrections to load.
        correction_type: 'classification' or 'extraction'.
        limit: Max results to return.

    Returns:
        List of correction dicts (the stored `value` payload, with `key`,
        `created_at`, and `updated_at` merged in for downstream consumers).
    """
    store = await get_memory_store()
    ns_map = {
        "classification": NS_CLASSIFICATION_CORRECTIONS,
        "extraction": NS_EXTRACTION_CORRECTIONS,
    }
    namespace = (ns_map.get(correction_type, correction_type), user_id)
    items = await store.asearch(namespace, limit=limit)
    return [_flatten_item(item) for item in items]


async def load_all_corrections(
    namespace_prefix: str,
    limit: int = 10_000,
) -> list[dict[str, Any]]:
    """Load every correction under a namespace across all users.

    Args:
        namespace_prefix: One of the `NS_*` constants (e.g.
            `NS_CLASSIFICATION_CORRECTIONS`).
        limit: Max results to return.

    Returns:
        List of correction dicts with `key`, `namespace`, `created_at`,
        and `updated_at` merged in.
    """
    store = await get_memory_store()
    items = await store.asearch((namespace_prefix,), limit=limit)
    return [_flatten_item(item) for item in items]


def _flatten_item(item: Any) -> dict[str, Any]:
    """Normalise a LangGraph `SearchItem` into a plain dict.

    Direct dict inputs (from the DictStore fallback) pass through unchanged.
    """
    if isinstance(item, dict):
        return item
    value = dict(getattr(item, "value", None) or {})
    namespace = getattr(item, "namespace", None)
    key = getattr(item, "key", None)
    created_at = getattr(item, "created_at", None)
    updated_at = getattr(item, "updated_at", None)
    if key is not None and "key" not in value:
        value["key"] = key
    if namespace is not None and "namespace" not in value:
        value["namespace"] = list(namespace) if isinstance(namespace, tuple) else namespace
    if created_at is not None and "created_at" not in value:
        value["created_at"] = str(created_at)
    if updated_at is not None and "updated_at" not in value:
        value["updated_at"] = str(updated_at)
    return value


def is_ephemeral_store() -> bool:
    """Return True when the active store does not persist across processes.

    InMemoryStore and the DictStore fallback are both ephemeral. The
    SQL-backed store is not. Harvest tooling warns the user when the store
    is ephemeral, since corrections written by a separate process (e.g. the
    API server) will not be visible.
    """
    if _store is None:
        return True
    name = type(_store).__name__
    if name in {"InMemoryStore", "DictStore"}:
        return True
    if name == "SqlAlchemyMemoryStore":
        return False
    module = type(_store).__module__ or ""
    return "memory" in module
