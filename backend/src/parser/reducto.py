"""Reducto Cloud API client for document parsing to markdown."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0


class ReductoParseError(Exception):
    """Raised when the Reducto API returns an error after retries."""


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


class ReductoClient:
    """Client for the Reducto Cloud document parsing API.

    Two-step process: upload file to get a reducto:// URI, then parse it.
    Ref: https://docs.reducto.ai/quickstart
    """

    def __init__(self, api_key: str, base_url: str) -> None:
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
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self._base_url}/parse",
                headers={
                    **self._auth_headers(),
                    "Content-Type": "application/json",
                },
                json={
                    "input": file_id,
                    "formatting": {"table_output_format": "md"},
                },
            )
            response.raise_for_status()
            data = response.json()

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
        )
