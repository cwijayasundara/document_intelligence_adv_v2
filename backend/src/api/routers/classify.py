"""Classification API endpoint: trigger classifier subagent."""

import logging
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.classifier import ClassifierSubagent
from src.api.dependencies import get_app_settings, get_current_user_id, get_run_guard, get_session
from src.api.middleware.run_guard import RunGuard
from src.api.schemas.classify import ClassifyResponse
from src.db.repositories.categories import CategoryRepository
from src.db.repositories.documents import DocumentRepository
from src.services.state_machine import InvalidTransitionError, validate_transition
from src.services.summarize_service import SummaryService

logger = logging.getLogger(__name__)

router = APIRouter()

_classifier: ClassifierSubagent | None = None


def _get_classifier() -> ClassifierSubagent:
    """Get or create the singleton ClassifierSubagent."""
    global _classifier
    if _classifier is None:
        _classifier = ClassifierSubagent()
    return _classifier


@router.post(
    "/classify/{doc_id}",
    response_model=ClassifyResponse,
    summary="Classify a document",
)
async def classify_document(
    doc_id: uuid.UUID,
    force: bool = False,
    session: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
    run_guard: RunGuard = Depends(get_run_guard),
) -> ClassifyResponse:
    """Classify a document. Returns cached result if already classified.

    Uses the document summary when available for more focused classification.
    Falls back to full parsed content otherwise. Pass force=true to re-classify.
    """
    repo = DocumentRepository(session)
    doc = await repo.get_by_id(doc_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Return cached classification if already classified and not forced
    if not force and doc.document_category_id is not None:
        cat_repo = CategoryRepository(session)
        cat = await cat_repo.get_by_id(doc.document_category_id)
        if cat is not None:
            logger.info("Returning cached classification for document %s", doc_id)
            return ClassifyResponse(
                document_id=doc_id,
                category_id=cat.id,
                category_name=cat.name,
                confidence=95,
                reasoning="Previously classified (cached result).",
                status=doc.status,
            )

    if not await run_guard.acquire(str(doc_id)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is already being processed",
        )
    try:
        try:
            validate_transition(doc.status, "classified")
        except InvalidTransitionError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        if not doc.parsed_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document has no parsed content",
            )

        path = Path(doc.parsed_path)
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parsed content file not found",
            )

        async with aiofiles.open(path, "r") as f:
            content = await f.read()

        # Try to load existing summary for more focused classification
        settings = get_app_settings()
        summary_service = SummaryService(summary_dir=settings.storage.summary_dir)
        cached_summary = await summary_service.get_cached_summary(doc_id)
        summary_text = cached_summary.get("summary") if cached_summary else None

        cat_repo = CategoryRepository(session)
        categories = await cat_repo.list_all()
        cat_dicts = [
            {
                "id": c.id,
                "name": c.name,
                "classification_criteria": c.classification_criteria,
            }
            for c in categories
        ]

        classifier = _get_classifier()
        source = "summary" if summary_text else "full content"
        logger.info(
            "Classifying document %s (%s) against %d categories using %s",
            doc_id,
            doc.file_name,
            len(cat_dicts),
            source,
        )
        result = await classifier.classify(
            file_name=doc.file_name,
            content=content,
            categories=cat_dicts,
            summary=summary_text,
        )
        logger.info(
            "Document %s classified as '%s' (confidence=%d%%)",
            doc_id,
            result.category_name,
            result.confidence,
        )

        doc.document_category_id = result.category_id
        doc.status = "classified"
        await session.flush()

        from src.audit import emit_audit_event

        emit_audit_event(
            event_type="document.classified",
            entity_id=str(doc_id),
            document_id=str(doc_id),
            file_name=doc.file_name,
            details={"category": result.category_name, "confidence": result.confidence},
        )
        return ClassifyResponse(
            document_id=doc_id,
            category_id=result.category_id,
            category_name=result.category_name,
            confidence=result.confidence,
            reasoning=result.reasoning,
            status="classified",
        )
    finally:
        await run_guard.release(str(doc_id))
