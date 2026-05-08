"""Data types and exceptions for the Reducto Cloud API client."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
    confidence_pct: float
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
class ReductoCitation:
    """A single citation pointing into the source document.

    Coordinates are page-normalized (0-1) for PDFs/images. For spreadsheets
    they are integer cell positions and ``page`` is the sheet index.
    """

    page: int
    left: float
    top: float
    width: float
    height: float
    content: str = ""
    confidence: str = "medium"


@dataclass
class ReductoExtractedField:
    """Normalized field from Reducto Extract."""

    field_name: str
    extracted_value: str
    source_text: str
    confidence: str = "medium"
    citations: list[ReductoCitation] = field(default_factory=list)


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
