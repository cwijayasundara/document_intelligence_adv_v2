"""Reducto Cloud API client implementation."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import httpx

from src.parser.reducto._helpers import (
    build_parse_result,
    chunk_metadata,
    classification_confidence,
    classification_reasoning,
    criteria_list,
    extract_fields_from_response,
    extraction_schema,
)
from src.parser.reducto.types import (
    ParseResult,
    ReductoChunkResult,
    ReductoClassificationResult,
    ReductoExtractionResult,
    ReductoParseError,
    ReductoProcessingError,
    ReductoRetrievalChunk,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0


class ReductoClient:
    """Client for the Reducto Cloud document parsing API.

    Two-step process: upload file to get a reducto:// URI, then parse it.
    Ref: https://docs.reducto.ai/quickstart
    """

    def __init__(self, api_key: str, base_url: str = "https://platform.reducto.ai") -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    async def parse(self, file_path: str | Path) -> ParseResult:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_id = await self._upload_file(path)
        return await self._parse_with_retries(file_id)

    async def classify(
        self,
        file_path: str | Path,
        categories: list[dict[str, Any]],
    ) -> ReductoClassificationResult:
        file_id = await self._upload_file(Path(file_path))
        logger.info(
            "Calling Reducto /classify for input=%s categories=%d",
            file_id,
            len(categories),
        )
        payload = {
            "input": file_id,
            "classification_schema": [
                {
                    "category": c["name"],
                    "criteria": criteria_list(c.get("classification_criteria")),
                }
                for c in categories
            ],
        }
        data = await self._post_json("/classify", payload, timeout=120.0)
        category_name = str(data.get("result", {}).get("category", ""))
        confidence = classification_confidence(data, category_name)
        logger.info(
            "Reducto /classify complete job_id=%s category=%s confidence=%d%%",
            data.get("job_id", "unknown"),
            category_name or "unknown",
            confidence,
        )
        return ReductoClassificationResult(
            category_name=category_name,
            confidence=confidence,
            reasoning=classification_reasoning(data, category_name),
            raw=data,
        )

    async def extract(
        self,
        file_path_or_input: str | Path,
        extraction_fields: list[dict[str, Any]],
    ) -> ReductoExtractionResult:
        input_ref = str(file_path_or_input)
        if not input_ref.startswith(("reducto://", "jobid://", "http://", "https://")):
            input_ref = await self._upload_file(Path(file_path_or_input))

        logger.info(
            "Calling Reducto /extract for input=%s fields=%d citations=true",
            input_ref,
            len(extraction_fields),
        )
        payload = {
            "input": input_ref,
            "instructions": {
                "schema": extraction_schema(extraction_fields),
                "system_prompt": (
                    "Extract the requested Private Equity document fields. "
                    "Return null for fields that are not present."
                ),
            },
            "settings": {
                "citations": {
                    "enabled": True,
                    "numerical_confidence": True,
                }
            },
        }
        data = await self._post_json("/extract", payload, timeout=300.0)
        result = ReductoExtractionResult(
            fields=extract_fields_from_response(data, extraction_fields),
            raw=data,
        )
        logger.info(
            "Reducto /extract complete job_id=%s fields=%d",
            data.get("job_id", "unknown"),
            len(result.fields),
        )
        return result

    async def parse_with_retrieval_chunks(
        self,
        file_path: str | Path,
        *,
        chunk_size: int = 1000,
        chunk_mode: str = "variable",
    ) -> ReductoChunkResult:
        file_id = await self._upload_file(Path(file_path))
        data = await self._parse_file_raw(
            file_id,
            retrieval={
                "chunking": {
                    "chunk_mode": chunk_mode,
                    "chunk_size": chunk_size,
                }
            },
        )
        chunks = []
        for idx, chunk in enumerate(data.get("result", {}).get("chunks", [])):
            metadata = chunk_metadata(chunk)
            chunks.append(
                ReductoRetrievalChunk(
                    text=str(chunk.get("content", "")),
                    index=idx,
                    metadata={"provider": "reducto", **metadata},
                )
            )
        return ReductoChunkResult(chunks=chunks, job_id=str(data.get("job_id", "")))

    async def _upload_file(self, path: Path) -> str:
        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    with open(path, "rb") as f:
                        response = await client.post(
                            f"{self._base_url}/upload",
                            headers=self._auth_headers(),
                            files={"file": (path.name, f, "application/octet-stream")},
                        )
                    response.raise_for_status()
                    data = response.json()

                file_id: str = data.get("file_id", "")
                if not file_id:
                    raise ReductoParseError(f"Upload returned no file_id: {data}")

                logger.info("Uploaded %s -> %s", path.name, file_id)
                return file_id

            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                last_error = exc
                logger.warning(
                    "Reducto upload attempt %d/%d failed: %s",
                    attempt,
                    MAX_RETRIES,
                    exc,
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_BACKOFF_BASE**attempt)

        raise ReductoParseError(f"Reducto upload failed after {MAX_RETRIES} retries: {last_error}")

    async def _parse_with_retries(self, file_id: str) -> ParseResult:
        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return await self._parse_file(file_id)
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                last_error = exc
                logger.warning(
                    "Reducto parse attempt %d/%d failed: %s",
                    attempt,
                    MAX_RETRIES,
                    exc,
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_BACKOFF_BASE**attempt)

        raise ReductoParseError(f"Reducto parsing failed after {MAX_RETRIES} retries: {last_error}")

    async def _parse_file(self, file_id: str) -> ParseResult:
        data = await self._parse_file_raw(file_id)
        return build_parse_result(data)

    async def _parse_file_raw(
        self,
        file_id: str,
        *,
        retrieval: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "input": file_id,
            "formatting": {"table_output_format": "md"},
        }
        if retrieval is not None:
            payload["retrieval"] = retrieval
        return await self._post_json("/parse", payload, timeout=300.0)

    async def _post_json(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        timeout: float,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self._base_url}{path}",
                headers={
                    **self._auth_headers(),
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise ReductoProcessingError(f"Reducto {path} returned non-object response")
        return data
