"""Interrupt nodes for human-in-the-loop review gates.

These nodes use LangGraph's interrupt() to pause pipeline execution.
When resumed, they re-read the updated data from disk/DB.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from langgraph.types import interrupt

from src.bulk.state import DocumentState

logger = logging.getLogger(__name__)


async def _update_doc_status(doc_id: str, status: str) -> None:
    """Persist document status to DB."""
    try:
        from src.db.connection import get_session_factory
        from src.db.repositories.documents import DocumentRepository

        factory = get_session_factory()
        async with factory() as session:
            repo = DocumentRepository(session)
            doc = await repo.get_by_id(uuid.UUID(doc_id))
            if doc:
                doc.status = status
                await session.commit()
    except Exception as exc:
        logger.error("[wait:%s] Failed to update status: %s", doc_id[:8], exc)


async def await_parse_review_node(state: DocumentState) -> dict[str, Any]:
    """Pause pipeline for human review of low-confidence parse output.

    Sets document status to awaiting_parse_review, then calls interrupt().
    On resume, re-reads edited content from disk.
    """
    doc_id = state.get("document_id", "")
    confidence = state.get("parse_confidence_pct", 0.0)

    logger.info(
        "[wait:%s] Pausing for parse review (confidence=%.1f%%)",
        doc_id[:8],
        confidence,
    )

    await _update_doc_status(doc_id, "awaiting_parse_review")

    # Pause execution — resumes when user approves edited content
    interrupt(
        {
            "reason": "parse_confidence_below_threshold",
            "document_id": doc_id,
            "confidence_pct": confidence,
            "action_required": "Review and edit parsed content, then resume",
        }
    )

    logger.info("[wait:%s] Resumed from parse review", doc_id[:8])

    # Re-read edited content from disk
    updated_content = state.get("parsed_content", "")
    try:
        from src.config.settings import get_settings
        from src.storage.local import LocalStorage

        settings = get_settings()
        storage = LocalStorage(
            upload_dir=settings.storage.upload_dir,
            parsed_dir=settings.storage.parsed_dir,
        )
        parsed_path = state.get("parsed_path", "")
        if parsed_path:
            updated_content = storage.read_parsed(parsed_path)
    except Exception as exc:
        logger.warning("[wait:%s] Could not re-read edited content: %s", doc_id[:8], exc)

    await _update_doc_status(doc_id, "processing")

    return {
        "parsed_content": updated_content,
        "requires_parse_review": False,
        "status": "edited",
        "pipeline_context": {
            **state.get("pipeline_context", {}),
            "user_edits_applied": True,
        },
    }


async def await_extraction_review_node(
    state: DocumentState,
) -> dict[str, Any]:
    """Pause pipeline for human review of low-confidence extractions.

    Sets document status to awaiting_extraction_review, then calls
    interrupt(). On resume, extraction results have been approved.
    """
    doc_id = state.get("document_id", "")
    results: list[dict[str, Any]] = state.get("extraction_results", [])  # type: ignore[assignment]
    review_count = sum(1 for r in results if r.get("requires_review"))

    logger.info(
        "[wait:%s] Pausing for extraction review (%d fields)",
        doc_id[:8],
        review_count,
    )

    await _update_doc_status(doc_id, "awaiting_extraction_review")

    # Pause execution — resumes when user approves all flagged fields
    interrupt(
        {
            "reason": "extraction_fields_require_review",
            "document_id": doc_id,
            "fields_requiring_review": review_count,
            "action_required": "Review flagged extraction fields, then resume",
        }
    )

    logger.info("[wait:%s] Resumed from extraction review", doc_id[:8])

    await _update_doc_status(doc_id, "processing")

    return {
        "requires_extraction_review": False,
        "status": "extracted",
    }
