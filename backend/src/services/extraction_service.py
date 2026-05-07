"""Extraction service with disk caching and DB persistence.

Orchestrates extractor → judge flow with content-hash based caching.
Results are saved to both the database and data/extraction/{doc_id}.json.
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

import aiofiles

logger = logging.getLogger(__name__)

CONFIDENCE_LOW = "low"


class ExtractionService:
    """Orchestrate field extraction with disk caching and confidence judging."""

    def __init__(
        self,
        extraction_dir: str = "./data/extraction",
    ) -> None:
        self._extraction_dir = Path(extraction_dir)
        self._extraction_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, doc_id: uuid.UUID) -> Path:
        return self._extraction_dir / f"{doc_id}.json"

    async def get_cached(self, doc_id: uuid.UUID, content_hash: str) -> list[dict[str, Any]] | None:
        """Return cached extraction results if content hash matches."""
        cached = await self._read_from_disk(doc_id)
        if cached and cached.get("content_hash") == content_hash:
            logger.info("Extraction cache hit for document %s", doc_id)
            return cached.get("results", [])
        return None

    async def extract_and_judge(
        self,
        doc_id: uuid.UUID,
        parsed_content: str,
        extraction_fields: list[dict[str, Any]],
        *,
        original_path: str | None = None,
        force: bool = False,
    ) -> list[dict[str, Any]]:
        """Run extraction then judge, with disk caching.

        Args:
            doc_id: Document UUID for cache key.
            parsed_content: Document markdown content.
            extraction_fields: Field definitions with field_id, field_name, etc.
            force: Skip cache and re-extract.

        Returns:
            List of result dicts with merged confidence data.
        """
        content_hash = self._compute_hash(parsed_content)

        # Check disk cache
        if not force:
            cached = await self.get_cached(doc_id, content_hash)
            if cached is not None:
                return cached

        results = await self._run_provider(
            doc_id=doc_id,
            parsed_content=parsed_content,
            extraction_fields=extraction_fields,
            original_path=original_path,
            force=force,
        )

        # Persist to disk
        await self._write_to_disk(doc_id, content_hash, results)

        low_count = sum(1 for r in results if r["requires_review"])
        logger.info(
            "Extraction complete: %d fields, %d require review",
            len(results),
            low_count,
        )
        return results

    async def _run_provider(
        self,
        *,
        doc_id: uuid.UUID,
        parsed_content: str,
        extraction_fields: list[dict[str, Any]],
        original_path: str | None,
        force: bool,
    ) -> list[dict[str, Any]]:
        from src.config.settings import get_settings
        from src.parser.reducto import ReductoClient
        from src.services.processing_providers import get_extraction_provider

        settings = get_settings()
        reducto = ReductoClient(
            api_key=settings.reducto_api_key,
            base_url=settings.reducto_base_url,
        )
        provider = get_extraction_provider(settings.processing, reducto)
        try:
            logger.info(
                "Extracting %d fields with %s",
                len(extraction_fields),
                settings.processing.extraction_provider,
            )
            return await provider.extract_and_judge(
                doc_id=doc_id,
                parsed_content=parsed_content,
                extraction_fields=extraction_fields,
                original_path=original_path,
                force=force,
            )
        except Exception:
            if (
                settings.processing.extraction_provider == "langgraph"
                or not settings.processing.fallback_to_legacy
            ):
                raise
            logger.exception("Reducto extraction failed; falling back to LangGraph extractor")
            from src.services.processing_providers import LangGraphExtractionProvider

            return await LangGraphExtractionProvider().extract_and_judge(
                doc_id=doc_id,
                parsed_content=parsed_content,
                extraction_fields=extraction_fields,
                original_path=original_path,
                force=force,
            )

    async def _read_from_disk(self, doc_id: uuid.UUID) -> dict[str, Any] | None:
        path = self._cache_path(doc_id)
        if not path.exists():
            return None
        try:
            async with aiofiles.open(path, "r") as f:
                return json.loads(await f.read())
        except (json.JSONDecodeError, OSError):
            return None

    async def _write_to_disk(
        self,
        doc_id: uuid.UUID,
        content_hash: str,
        results: list[dict[str, Any]],
    ) -> None:
        path = self._cache_path(doc_id)
        data = {
            "document_id": str(doc_id),
            "content_hash": content_hash,
            "results": results,
        }
        async with aiofiles.open(path, "w") as f:
            await f.write(json.dumps(data, indent=2))
        logger.info("Extraction results cached to %s", path)

    @staticmethod
    def _compute_hash(content: str) -> str:
        from src.services.hashing import compute_content_hash

        return compute_content_hash(content)
