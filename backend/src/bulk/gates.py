"""Routing functions for conditional edges in the unified pipeline.

These functions decide whether to pause for human review or continue
automatically, based on confidence scores. Applied equally to single
and bulk documents — the logic is purely data-driven.
"""

from __future__ import annotations

import logging
from typing import Any

from src.bulk.state import DocumentState

logger = logging.getLogger(__name__)

_DEFAULT_PARSE_CONFIDENCE_THRESHOLD = 90.0


def _get_parse_threshold() -> float:
    """Get parse confidence threshold from settings or use default."""
    try:
        from src.config.settings import get_settings

        return getattr(
            get_settings(),
            "parse_confidence_threshold",
            _DEFAULT_PARSE_CONFIDENCE_THRESHOLD,
        )
    except Exception:
        return _DEFAULT_PARSE_CONFIDENCE_THRESHOLD


def route_after_parse(state: DocumentState) -> str:
    """Route after parse node based on parse confidence.

    If confidence >= threshold, continue to summarize.
    If confidence < threshold, pause for human edit.

    Returns:
        "summarize" to continue, or "await_parse_review" to pause.
    """
    confidence = state.get("parse_confidence_pct", 100.0)
    doc_id = state.get("document_id", "unknown")[:8]
    threshold = _get_parse_threshold()

    if confidence >= threshold:
        logger.info(
            "[gate:%s] Parse confidence %.1f%% >= %.0f%%, continuing",
            doc_id,
            confidence,
            threshold,
        )
        return "summarize"

    logger.info(
        "[gate:%s] Parse confidence %.1f%% < %.0f%%, pausing for review",
        doc_id,
        confidence,
        threshold,
    )
    return "await_parse_review"


def route_after_extract(state: DocumentState) -> str:
    """Route after extract node based on extraction review flags.

    If no fields require review, continue to ingest.
    If any fields require review, pause for human review.

    Returns:
        "ingest" to continue, or "await_extraction_review" to pause.
    """
    doc_id = state.get("document_id", "unknown")[:8]
    extraction_results: list[dict[str, Any]] = state.get("extraction_results", [])  # type: ignore[assignment]

    needs_review = any(r.get("requires_review", False) for r in extraction_results)

    if not needs_review:
        logger.info("[gate:%s] No fields require review, continuing", doc_id)
        return "ingest"

    review_count = sum(1 for r in extraction_results if r.get("requires_review"))
    logger.info(
        "[gate:%s] %d fields require review, pausing",
        doc_id,
        review_count,
    )
    return "await_extraction_review"
