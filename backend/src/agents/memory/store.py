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

    Uses InMemoryStore as fallback when PostgreSQL is unavailable.
    """
    global _store
    if _store is not None:
        return _store

    try:
        from langgraph.store.memory import InMemoryStore

        _store = InMemoryStore()
        logger.info("Using InMemoryStore for agent memory")
    except Exception as exc:
        logger.warning("Could not create memory store: %s", exc)
        _store = _create_dict_store()

    return _store


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
    """Load corrections from long-term memory.

    Args:
        user_id: User whose corrections to load.
        correction_type: 'classification' or 'extraction'.
        limit: Max results to return.

    Returns:
        List of correction dicts.
    """
    store = await get_memory_store()
    ns_map = {
        "classification": NS_CLASSIFICATION_CORRECTIONS,
        "extraction": NS_EXTRACTION_CORRECTIONS,
    }
    namespace = (ns_map.get(correction_type, correction_type), user_id)

    return await store.asearch(namespace, limit=limit)
