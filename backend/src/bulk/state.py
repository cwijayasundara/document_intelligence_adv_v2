"""Document state definition for the bulk processing pipeline."""

from __future__ import annotations

from typing import Any, TypedDict


class DocumentState(TypedDict, total=False):
    """State carried through the bulk pipeline per document.

    All fields are optional (total=False) to support incremental
    population as the document moves through pipeline nodes.
    """

    document_id: str
    status: str
    parsed_content: str
    classification_result: dict[str, Any]
    extraction_results: list[dict[str, Any]]
    judge_results: list[dict[str, Any]]
    summary: str
    error: str | None
    start_time_ms: float
    end_time_ms: float
    node_timings: dict[str, float]
