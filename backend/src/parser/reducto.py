"""Reducto Cloud API client for document parsing to markdown."""

from __future__ import annotations

import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

REDUCTO_BASE_URL = "https://platform.reducto.ai"
MAX_RETRIES = 3


class ReductoParseError(Exception):
    """Raised when the Reducto API returns an error after retries."""


class ReductoClient:
    """Client for the Reducto Cloud document parsing API.

    Two-step process: upload file to get file_id, then parse using that ID.
    """

    def __init__(self, api_key: str, base_url: str = REDUCTO_BASE_URL) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    async def parse(self, file_path: str | Path) -> str:
        """Parse a document file and return markdown content.

        Args:
            file_path: Path to the document file.

        Returns:
            Parsed markdown string with chunks joined by newlines.

        Raises:
            ReductoParseError: If parsing fails after retries.
            FileNotFoundError: If the file does not exist.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                file_id = await self._upload_file(path)
                return await self._parse_file(file_id)
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                last_error = exc
                logger.warning(
                    "Reducto parse attempt %d/%d failed: %s",
                    attempt,
                    MAX_RETRIES,
                    exc,
                )

        raise ReductoParseError(f"Reducto parsing failed after {MAX_RETRIES} retries: {last_error}")

    async def _upload_file(self, path: Path) -> str:
        """Upload a file to Reducto and return the file_id."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            with open(path, "rb") as f:
                response = await client.post(
                    f"{self._base_url}/upload",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    files={"file": (path.name, f, "application/octet-stream")},
                )
            response.raise_for_status()
            data = response.json()
            file_id = data.get("file_id", "")
            if not file_id:
                raise ReductoParseError(f"Upload returned no file_id: {data}")
            logger.info("Uploaded %s → file_id=%s", path.name, file_id)
            return file_id

    async def _parse_file(self, file_id: str) -> str:
        """Parse an uploaded file by file_id and return markdown."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self._base_url}/parse",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={"input": file_id},
            )
            response.raise_for_status()
            data = response.json()

        result = data.get("result", {})
        chunks = result.get("chunks", [])
        if chunks:
            return "\n\n".join(chunk.get("content", "") for chunk in chunks)
        return result.get("content", "")
