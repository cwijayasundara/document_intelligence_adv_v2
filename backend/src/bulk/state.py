"""Document state definition for the bulk processing pipeline."""

from __future__ import annotations

from typing import Any, TypedDict


class DocumentState(TypedDict, total=False):
    """State carried through the bulk pipeline per document.

    All fields are optional (total=False) to support incremental
    population as the document moves through pipeline nodes.
    """

    document_id: str
    file_name: str
    original_path: str
    parsed_path: str
    status: str
    parsed_content: str
    summary_text: str
    classification_result: dict[str, Any]
    category_id: str
    category_name: str
    extraction_results: list[dict[str, Any]]
    judge_results: list[dict[str, Any]]
    categories: list[dict[str, Any]]
    extraction_fields: list[dict[str, Any]]
    extraction_fields_map: dict[str, list[dict[str, Any]]]
    chunks_created: int
    error: str | None
    start_time_ms: float
    end_time_ms: float
    node_timings: dict[str, float]

    # Pipeline tracking
    parse_confidence_pct: float
    requires_parse_review: bool
    requires_extraction_review: bool
    node_statuses: dict[str, dict[str, Any]]
    pipeline_context: dict[str, Any]
