"""Extraction service with disk caching and DB persistence.

Orchestrates extractor → judge flow with content-hash based caching.
Results are saved to both the database and data/extraction/{doc_id}.json.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from pathlib import Path
from typing import Any

import aiofiles

from src.agents.extractor import ExtractorSubagent
from src.agents.judge import JudgeSubagent

logger = logging.getLogger(__name__)

CONFIDENCE_LOW = "low"


class ExtractionService:
    """Orchestrate field extraction with disk caching and confidence judging."""

    def __init__(
        self,
        extraction_dir: str = "./data/extraction",
        extractor: ExtractorSubagent | None = None,
        judge: JudgeSubagent | None = None,
    ) -> None:
        self._extractor = extractor or ExtractorSubagent()
        self._judge = judge or JudgeSubagent()
        self._extraction_dir = Path(extraction_dir)
        self._extraction_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, doc_id: uuid.UUID) -> Path:
        return self._extraction_dir / f"{doc_id}.json"

    async def get_cached(
        self, doc_id: uuid.UUID, content_hash: str
    ) -> list[dict[str, Any]] | None:
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

        logger.info(
            "Extracting %d fields from content (%d chars)",
            len(extraction_fields),
            len(parsed_content),
        )
        extraction_result = await self._extractor.extract(
            parsed_content, extraction_fields
        )

        logger.info("Judging %d extracted fields", len(extraction_result.fields))
        judge_result = await self._judge.evaluate(
            extraction_result.fields,
            parsed_content,
            field_metadata=extraction_fields,
        )

        eval_map = {e.field_name: e for e in judge_result.evaluations}

        results = []
        for i, field_def in enumerate(extraction_fields):
            extracted = (
                extraction_result.fields[i]
                if i < len(extraction_result.fields)
                else None
            )
            evaluation = eval_map.get(field_def["field_name"])

            confidence = evaluation.confidence if evaluation else "medium"
            reasoning = evaluation.reasoning if evaluation else ""
            value = extracted.extracted_value if extracted else ""
            is_required = field_def.get("required", False)
            requires_review = (
                confidence == CONFIDENCE_LOW
                or (confidence == "medium" and not value)
                or (is_required and not value)
            )

            results.append(
                {
                    "field_id": str(field_def["field_id"]),
                    "field_name": field_def["field_name"],
                    "display_name": field_def.get("display_name", ""),
                    "extracted_value": value,
                    "source_text": extracted.source_text if extracted else "",
                    "confidence": confidence,
                    "confidence_reasoning": reasoning,
                    "requires_review": requires_review,
                }
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
        return hashlib.sha256(content.encode()).hexdigest()
