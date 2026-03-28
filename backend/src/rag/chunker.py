"""Semantic chunker for splitting document content.

Uses recursive character text splitting with configurable chunk size
and overlap. Falls back gracefully if langchain is not available.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A single text chunk with metadata."""

    text: str
    index: int
    start_char: int
    end_char: int


class SemanticChunker:
    """Split parsed markdown on semantic boundaries.

    Uses a simple recursive splitting approach with configurable
    max_tokens and overlap. Splits on paragraphs, then sentences,
    then characters.
    """

    def __init__(
        self,
        max_tokens: int = 512,
        overlap_tokens: int = 100,
        chars_per_token: int = 4,
    ) -> None:
        self._max_chars = max_tokens * chars_per_token
        self._overlap_chars = overlap_tokens * chars_per_token

    @property
    def max_chars(self) -> int:
        """Return the max characters per chunk."""
        return self._max_chars

    @property
    def overlap_chars(self) -> int:
        """Return the overlap characters between chunks."""
        return self._overlap_chars

    def chunk(self, text: str) -> list[Chunk]:
        """Split text into semantic chunks.

        Args:
            text: The full document text to chunk.

        Returns:
            List of Chunk objects with text, index, and position info.
        """
        if not text.strip():
            return []

        separators = ["\n\n", "\n", ". ", " "]
        raw_chunks = self._recursive_split(text, separators)

        chunks = []
        for idx, (chunk_text, start) in enumerate(raw_chunks):
            chunks.append(Chunk(
                text=chunk_text,
                index=idx,
                start_char=start,
                end_char=start + len(chunk_text),
            ))
        return chunks

    def _recursive_split(
        self,
        text: str,
        separators: list[str],
    ) -> list[tuple[str, int]]:
        """Recursively split text using separators."""
        if len(text) <= self._max_chars:
            return [(text.strip(), 0)] if text.strip() else []

        sep = separators[0] if separators else ""
        remaining_seps = separators[1:] if len(separators) > 1 else []

        if sep and sep in text:
            parts = text.split(sep)
        else:
            if remaining_seps:
                return self._recursive_split(text, remaining_seps)
            return self._split_by_size(text)

        result: list[tuple[str, int]] = []
        current = ""
        current_start = 0
        pos = 0

        for part in parts:
            candidate = current + sep + part if current else part

            if len(candidate) > self._max_chars and current:
                result.append((current.strip(), current_start))
                overlap_start = max(
                    0, len(current) - self._overlap_chars
                )
                current = current[overlap_start:] + sep + part
                current_start = pos - len(current) + len(part) + len(sep)
            else:
                current = candidate
                if not result:
                    current_start = pos

            pos += len(part) + len(sep)

        if current.strip():
            result.append((current.strip(), current_start))

        return result

    def _split_by_size(self, text: str) -> list[tuple[str, int]]:
        """Fall back to splitting by character size."""
        result: list[tuple[str, int]] = []
        start = 0
        while start < len(text):
            end = min(start + self._max_chars, len(text))
            chunk = text[start:end].strip()
            if chunk:
                result.append((chunk, start))
            start = end - self._overlap_chars if end < len(text) else end
        return result
