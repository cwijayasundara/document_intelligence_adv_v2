"""Extraction API endpoints with review gate enforcement."""

import logging
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user_id, get_run_guard, get_session
from src.api.middleware.run_guard import RunGuard
from src.api.schemas.extract import (
    ExtractionResponse,
    ExtractionResultItem,
    ExtractionResultsResponse,
    ExtractionUpdateRequest,
    ExtractionUpdateResponse,
)
from src.db.repositories.documents import DocumentRepository
from src.db.repositories.extracted_values import ExtractedValuesRepository
from src.db.repositories.extraction import (
    ExtractionFieldRepository,
    ExtractionSchemaRepository,
)
from src.services.extraction_service import ExtractionService
from src.services.state_machine import InvalidTransitionError, validate_transition

logger = logging.getLogger(__name__)

router = APIRouter()

_extraction_service: ExtractionService | None = None


def _get_extraction_service() -> ExtractionService:
    """Get or create the singleton ExtractionService."""
    global _extraction_service
    if _extraction_service is None:
        _extraction_service = ExtractionService()
    return _extraction_service


@router.post(
    "/extract/{doc_id}",
    response_model=ExtractionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Extract fields from document",
)
async def extract_document(
    doc_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),  # noqa: ARG001
    run_guard: RunGuard = Depends(get_run_guard),
) -> ExtractionResponse:
    """Run extraction + judge on a document, save results."""
    if not await run_guard.acquire(str(doc_id)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is already being processed",
        )
    try:
        doc_repo = DocumentRepository(session)
        doc = await doc_repo.get_by_id(doc_id)
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        try:
            validate_transition(doc.status, "extracted")
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

        field_defs = await _load_extraction_fields(session, doc.document_category_id)

        service = _get_extraction_service()
        logger.info("Starting extraction for document %s (%d fields)", doc_id, len(field_defs))
        results = await service.extract_and_judge(content, field_defs)

        ev_repo = ExtractedValuesRepository(session)
        saved = await ev_repo.save_results(doc_id, results)

        review_count = sum(1 for r in results if r["requires_review"])
        logger.info(
            "Extraction saved for %s: %d results, %d need review",
            doc_id, len(saved), review_count,
        )

        doc.status = "extracted"
        await session.flush()

        items = [
            ExtractionResultItem(
                id=saved[i].id,
                field_name=results[i]["field_name"],
                display_name=results[i]["display_name"],
                extracted_value=results[i]["extracted_value"],
                source_text=results[i]["source_text"],
                confidence=results[i]["confidence"],
                confidence_reasoning=results[i]["confidence_reasoning"],
                requires_review=results[i]["requires_review"],
                reviewed=False,
            )
            for i in range(len(saved))
        ]

        return ExtractionResponse(
            document_id=doc_id,
            status="extracted",
            results=items,
            requires_review_count=review_count,
        )
    finally:
        await run_guard.release(str(doc_id))


@router.get(
    "/extract/{doc_id}/results",
    response_model=ExtractionResultsResponse,
    summary="Get extraction results",
)
async def get_extraction_results(
    doc_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),  # noqa: ARG001
) -> ExtractionResultsResponse:
    """Get extraction results for a document."""
    doc_repo = DocumentRepository(session)
    doc = await doc_repo.get_by_id(doc_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    ev_repo = ExtractedValuesRepository(session)
    values = await ev_repo.get_by_document_id(doc_id)
    if not values:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No extraction results for this document",
        )

    items = []
    for v in values:
        field_name = ""
        display_name = ""
        if v.field:
            field_name = v.field.field_name
            display_name = v.field.display_name
        items.append(
            ExtractionResultItem(
                id=v.id,
                field_name=field_name,
                display_name=display_name,
                extracted_value=v.extracted_value,
                source_text=v.source_text,
                confidence=v.confidence,
                confidence_reasoning=v.confidence_reasoning,
                requires_review=v.requires_review,
                reviewed=v.reviewed,
            )
        )

    review_count = sum(1 for v in values if v.requires_review and not v.reviewed)
    all_reviewed = review_count == 0

    return ExtractionResultsResponse(
        document_id=doc_id,
        results=items,
        requires_review_count=review_count,
        all_reviewed=all_reviewed,
    )


@router.put(
    "/extract/{doc_id}/results",
    response_model=ExtractionUpdateResponse,
    summary="Update extraction results",
)
async def update_extraction_results(
    doc_id: uuid.UUID,
    body: ExtractionUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),  # noqa: ARG001
) -> ExtractionUpdateResponse:
    """Update extracted values and check review gate."""
    doc_repo = DocumentRepository(session)
    doc = await doc_repo.get_by_id(doc_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    ev_repo = ExtractedValuesRepository(session)
    updates = [u.model_dump() for u in body.updates]
    updated_count = await ev_repo.update_values(updates)

    unreviewed = await ev_repo.get_unreviewed_fields(doc_id)
    review_count = len(unreviewed)
    all_reviewed = review_count == 0

    if not all_reviewed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot proceed: {review_count} fields require review",
            headers={},
        )

    return ExtractionUpdateResponse(
        document_id=doc_id,
        updated_count=updated_count,
        requires_review_count=review_count,
        all_reviewed=all_reviewed,
        can_proceed=all_reviewed,
    )


async def _load_extraction_fields(
    session: AsyncSession,
    category_id: uuid.UUID | None,
) -> list[dict]:
    """Load extraction field definitions for a category."""
    if category_id is None:
        return []

    schema_repo = ExtractionSchemaRepository(session)
    schema = await schema_repo.get_latest_for_category(category_id)
    if schema is None:
        return []

    field_repo = ExtractionFieldRepository(session)
    fields = await field_repo.get_fields_for_schema(schema.id)

    return [
        {
            "field_id": f.id,
            "field_name": f.field_name,
            "display_name": f.display_name,
            "description": f.description,
            "data_type": f.data_type,
            "examples": f.examples,
        }
        for f in fields
    ]
