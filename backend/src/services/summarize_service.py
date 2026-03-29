"""Summarization service with content hash caching."""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any

from src.agents.summarizer import SummarizerSubagent

logger = logging.getLogger(__name__)


class SummaryService:
    """Orchestrate document summarization with caching."""

    def __init__(self, summarizer: SummarizerSubagent | None = None) -> None:
        self._summarizer = summarizer or SummarizerSubagent()
        self._cache: dict[str, dict[str, Any]] = {}

    async def generate_summary(
        self,
        doc_id: uuid.UUID,
        parsed_content: str,
    ) -> dict[str, Any]:
        """Generate or return cached summary for a document.

        Args:
            doc_id: Document UUID.
            parsed_content: Parsed markdown content.

        Returns:
            Dict with summary, key_topics, content_hash, cached flag.
        """
        content_hash = self._compute_hash(parsed_content)
        cache_key = str(doc_id)

        cached = self._cache.get(cache_key)
        if cached and cached.get("content_hash") == content_hash:
            logger.info("Summary cache hit for document %s", doc_id)
            return {**cached, "cached": True}

        logger.info("Generating summary for document %s (%d chars)", doc_id, len(parsed_content))
        result = await self._summarizer.summarize(parsed_content)

        summary_data = {
            "document_id": doc_id,
            "summary": result.summary,
            "key_topics": result.key_topics,
            "content_hash": content_hash,
            "cached": False,
        }
        self._cache[cache_key] = summary_data
        logger.info(
            "Summary generated for document %s: %d topics",
            doc_id,
            len(result.key_topics),
        )
        return summary_data

    def get_cached_summary(self, doc_id: uuid.UUID) -> dict[str, Any] | None:
        """Get a cached summary for a document.

        Returns:
            Cached summary dict or None.
        """
        return self._cache.get(str(doc_id))

    @staticmethod
    def _compute_hash(content: str) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()
