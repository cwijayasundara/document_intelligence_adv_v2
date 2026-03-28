"""Reducto Cloud API client for document parsing to markdown."""

from __future__ import annotations

import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

REDUCTO_API_URL = "https://platform.reducto.ai/parse"
MAX_RETRIES = 3


class ReductoParseError(Exception):
    """Raised when the Reducto API returns an error after retries."""

    pass


class ReductoClient:
    """Client for the Reducto Cloud document parsing API."""

    def __init__(self, api_key: str, api_url: str = REDUCTO_API_URL) -> None:
        self._api_key = api_key
        self._api_url = api_url

    async def parse(self, file_path: str | Path) -> str:
        """Parse a document file and return markdown content.

        Args:
            file_path: Path to the document file.

        Returns:
            Parsed markdown string.

        Raises:
            ReductoParseError: If parsing fails after MAX_RETRIES attempts.
            FileNotFoundError: If the file does not exist.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return await self._send_request(path)
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                last_error = exc
                logger.warning(
                    "Reducto parse attempt %d/%d failed: %s",
                    attempt,
                    MAX_RETRIES,
                    exc,
                )

        raise ReductoParseError(f"Reducto parsing failed after {MAX_RETRIES} retries: {last_error}")

    async def _send_request(self, path: Path) -> str:
        """Send a single parse request to Reducto."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            with open(path, "rb") as f:
                response = await client.post(
                    self._api_url,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    files={"file": (path.name, f, "application/octet-stream")},
                )
            response.raise_for_status()
            data = response.json()
            return data.get("result", {}).get("content", "")
