"""Summarization service with file-based persistence."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

import aiofiles

from src.agents.summarizer import summarize_document

logger = logging.getLogger(__name__)


class SummaryService:
    """Orchestrate document summarization with disk persistence."""

    def __init__(
        self,
        summary_dir: str = "./data/summary",
    ) -> None:
        self._summary_dir = Path(summary_dir)
        self._summary_dir.mkdir(parents=True, exist_ok=True)

    def _summary_path(self, doc_id: uuid.UUID) -> Path:
        return self._summary_dir / f"{doc_id}.json"

    async def generate_summary(
        self,
        doc_id: uuid.UUID,
        parsed_content: str,
        *,
        force: bool = False,
    ) -> dict[str, Any]:
        """Generate or return cached summary for a document."""
        content_hash = self._compute_hash(parsed_content)

        if not force:
            cached = await self._read_from_disk(doc_id)
            if cached and cached.get("content_hash") == content_hash:
                logger.info("Summary cache hit for document %s", doc_id)
                return {**cached, "cached": True}

        logger.info(
            "Generating summary for document %s (%d chars)",
            doc_id,
            len(parsed_content),
        )
        result = await summarize_document(parsed_content)

        summary_data: dict[str, Any] = {
            "document_id": str(doc_id),
            "summary": result.summary,
            "key_topics": result.key_topics,
            "content_hash": content_hash,
        }
        await self._write_to_disk(doc_id, summary_data)
        logger.info(
            "Summary generated for document %s: %d topics",
            doc_id,
            len(result.key_topics),
        )
        return {**summary_data, "cached": False}

    async def get_cached_summary(self, doc_id: uuid.UUID) -> dict[str, Any] | None:
        """Get a persisted summary for a document."""
        return await self._read_from_disk(doc_id)

    async def _read_from_disk(self, doc_id: uuid.UUID) -> dict[str, Any] | None:
        path = self._summary_path(doc_id)
        if not path.exists():
            return None
        try:
            async with aiofiles.open(path, "r") as f:
                return json.loads(await f.read())
        except (json.JSONDecodeError, OSError):
            return None

    async def _write_to_disk(self, doc_id: uuid.UUID, data: dict[str, Any]) -> None:
        path = self._summary_path(doc_id)
        async with aiofiles.open(path, "w") as f:
            await f.write(json.dumps(data, indent=2))

    @staticmethod
    def _compute_hash(content: str) -> str:
        from src.services.hashing import compute_content_hash

        return compute_content_hash(content)
