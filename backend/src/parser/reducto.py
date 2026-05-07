"""Reducto Cloud API client for document parsing to markdown."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0


class ReductoParseError(Exception):
    """Raised when the Reducto API returns an error after retries."""


class ReductoProcessingError(Exception):
    """Raised when a non-parse Reducto operation fails."""


@dataclass
class BlockConfidence:
    """Confidence info for a single parsed block."""

    block_type: str
    confidence: str  # "high" or "low"


@dataclass
class ParseResult:
    """Structured result from Reducto parse with confidence metadata."""

    content: str
    confidence_pct: float  # 0-100 overall confidence percentage
    block_confidences: list[BlockConfidence] = field(default_factory=list)
    has_low_confidence: bool = False
    job_id: str = ""

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.content == other
        if isinstance(other, ParseResult):
            return self.__dict__ == other.__dict__
        return NotImplemented


@dataclass
class ReductoClassificationResult:
    """Normalized result from Reducto Classify."""

    category_name: str
    confidence: int
    reasoning: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReductoExtractedField:
    """Normalized field from Reducto Extract."""

    field_name: str
    extracted_value: str
    source_text: str
    confidence: str = "medium"


@dataclass
class ReductoExtractionResult:
    """Normalized result from Reducto Extract."""

    fields: list[ReductoExtractedField] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReductoRetrievalChunk:
    """Chunk returned from Reducto Parse retrieval chunking."""

    text: str
    index: int
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class ReductoChunkResult:
    """Normalized Reducto retrieval chunking result."""

    chunks: list[ReductoRetrievalChunk] = field(default_factory=list)
    job_id: str = ""


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
        """Parse a document file and return structured result with confidence.

        Args:
            file_path: Path to the document file.

        Returns:
            ParseResult with markdown content and confidence metadata.

        Raises:
            ReductoParseError: If parsing fails after retries.
            FileNotFoundError: If the file does not exist.
        """
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
        """Classify a document with Reducto Classify."""
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
                    "criteria": _criteria_list(c.get("classification_criteria")),
                }
                for c in categories
            ],
        }
        data = await self._post_json("/classify", payload, timeout=120.0)
        category_name = str(data.get("result", {}).get("category", ""))
        confidence = _classification_confidence(data, category_name)
        logger.info(
            "Reducto /classify complete job_id=%s category=%s confidence=%d%%",
            data.get("job_id", "unknown"),
            category_name or "unknown",
            confidence,
        )
        return ReductoClassificationResult(
            category_name=category_name,
            confidence=confidence,
            reasoning=_classification_reasoning(data, category_name),
            raw=data,
        )

    async def extract(
        self,
        file_path_or_input: str | Path,
        extraction_fields: list[dict[str, Any]],
    ) -> ReductoExtractionResult:
        """Extract structured fields with Reducto Extract and citations enabled."""
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
                "schema": _extraction_schema(extraction_fields),
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
            fields=_extract_fields_from_response(data, extraction_fields),
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
        """Parse with Reducto retrieval chunking for RAG ingestion."""
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
            metadata = _chunk_metadata(chunk)
            chunks.append(
                ReductoRetrievalChunk(
                    text=str(chunk.get("content", "")),
                    index=idx,
                    metadata={"provider": "reducto", **metadata},
                )
            )
        return ReductoChunkResult(chunks=chunks, job_id=str(data.get("job_id", "")))

    async def _upload_file(self, path: Path) -> str:
        """Upload a file to Reducto and return the reducto:// URI.

        The upload endpoint returns a file_id already prefixed with
        ``reducto://``, e.g. ``reducto://abc123def456.pdf``.
        """
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
        """Call the /parse endpoint with retries and exponential backoff."""
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
        """Parse an uploaded file by its reducto:// URI and return structured result.

        Extracts block-level confidence from the Reducto response to compute
        an overall confidence percentage.
        """
        data = await self._parse_file_raw(file_id)

        job_id = data.get("job_id", "unknown")
        usage = data.get("usage", {})
        logger.info(
            "Parse complete job_id=%s pages=%s credits=%s",
            job_id,
            usage.get("num_pages", "?"),
            usage.get("credits", "?"),
        )

        result = data.get("result", {})
        chunks = result.get("chunks", [])
        if not chunks:
            raise ReductoParseError(
                f"Parse returned no chunks for job_id={job_id}: "
                f"result_type={result.get('type', 'unknown')}"
            )

        # Join content from all chunks
        content = "\n\n".join(chunk.get("content", "") for chunk in chunks)

        # Extract block-level confidence from chunks
        block_confidences: list[BlockConfidence] = []
        for chunk in chunks:
            for block in chunk.get("blocks", []):
                block_confidences.append(
                    BlockConfidence(
                        block_type=block.get("type", "Unknown"),
                        confidence=block.get("confidence", "high"),
                    )
                )

        # Compute overall confidence percentage
        if block_confidences:
            high_count = sum(1 for b in block_confidences if b.confidence == "high")
            confidence_pct = (high_count / len(block_confidences)) * 100
        else:
            # No block metadata available — assume high confidence
            confidence_pct = 100.0

        has_low = any(b.confidence == "low" for b in block_confidences)

        logger.info(
            "Parse confidence for job_id=%s: %.1f%% (%d blocks, %s low-confidence)",
            job_id,
            confidence_pct,
            len(block_confidences),
            "has" if has_low else "no",
        )

        return ParseResult(
            content=content,
            confidence_pct=round(confidence_pct, 1),
            block_confidences=block_confidences,
            has_low_confidence=has_low,
            job_id=job_id,
        )

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


def _criteria_list(criteria: Any) -> list[str]:
    if isinstance(criteria, list):
        return [str(item) for item in criteria if str(item).strip()]
    if isinstance(criteria, str) and criteria.strip():
        return [line.strip(" -") for line in criteria.splitlines() if line.strip(" -")]
    return ["matches this category"]


def _classification_confidence(data: dict[str, Any], category_name: str) -> int:
    categories = data.get("response_confidence", {}).get("categories", [])
    for item in categories:
        if item.get("category") == category_name:
            return round(float(item.get("confidence", 0.0)) * 100)
    return 50 if category_name else 0


def _classification_reasoning(data: dict[str, Any], category_name: str) -> str:
    categories = data.get("response_confidence", {}).get("categories", [])
    for item in categories:
        if item.get("category") != category_name:
            continue
        criteria = item.get("criteria_confidence", [])
        if not criteria:
            return "Reducto selected the best matching category."
        parts = [
            f"{c.get('criterion', 'criterion')}: {c.get('confidence', 'unknown')}"
            for c in criteria
        ]
        return "Reducto criteria confidence: " + "; ".join(parts)
    return "Reducto selected the best matching category."


def _extraction_schema(fields: list[dict[str, Any]]) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []
    type_map = {
        "string": "string",
        "number": "number",
        "date": "string",
        "currency": "string",
        "percentage": "string",
    }
    for field_def in fields:
        name = field_def["field_name"]
        properties[name] = {
            "type": type_map.get(field_def.get("data_type", "string"), "string"),
            "description": field_def.get("description") or field_def.get("display_name", ""),
        }
        if field_def.get("required"):
            required.append(name)
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _extract_fields_from_response(
    data: dict[str, Any],
    extraction_fields: list[dict[str, Any]],
) -> list[ReductoExtractedField]:
    raw_result = data.get("result", {})
    if isinstance(raw_result, list):
        result_obj = raw_result[0] if raw_result and isinstance(raw_result[0], dict) else {}
    elif isinstance(raw_result, dict):
        result_obj = raw_result
    else:
        result_obj = {}

    fields: list[ReductoExtractedField] = []
    for field_def in extraction_fields:
        name = field_def["field_name"]
        raw_value = result_obj.get(name)
        value, source, confidence = _unwrap_extracted_value(raw_value)
        fields.append(
            ReductoExtractedField(
                field_name=name,
                extracted_value=value,
                source_text=source,
                confidence=confidence,
            )
        )
    return fields


def _unwrap_extracted_value(raw_value: Any) -> tuple[str, str, str]:
    if isinstance(raw_value, dict) and "value" in raw_value:
        citations = raw_value.get("citations") or []
        first_citation = citations[0] if citations and isinstance(citations[0], dict) else {}
        value = raw_value.get("value")
        return (
            "" if value is None else str(value),
            str(first_citation.get("content", "")),
            str(first_citation.get("confidence", "medium")),
        )
    if raw_value is None:
        return "", "", "low"
    return str(raw_value), "", "medium"


def _chunk_metadata(chunk: dict[str, Any]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    blocks = chunk.get("blocks", [])
    if blocks and isinstance(blocks[0], dict):
        block = blocks[0]
        bbox = block.get("bbox", {})
        if isinstance(bbox, dict) and bbox.get("page") is not None:
            metadata["page"] = str(bbox["page"])
        if block.get("type") is not None:
            metadata["block_type"] = str(block["type"])
    return metadata
