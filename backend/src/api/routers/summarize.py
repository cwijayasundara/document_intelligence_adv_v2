"""Summarize API endpoints: generate and get summaries."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from src.api.dependencies import get_current_user_id, get_session
from src.api.schemas.summarize import SummarizeResponse, SummaryGetResponse
from src.db.repositories.documents import DocumentRepository
from src.services.state_machine import InvalidTransitionError, validate_transition
from src.services.summarize_service import SummaryService

router = APIRouter()

_summary_service: SummaryService | None = None


def _get_summary_service() -> SummaryService:
    """Get or create the singleton SummaryService."""
    global _summary_service
    if _summary_service is None:
        _summary_service = SummaryService()
    return _summary_service


@router.post(
    "/summarize/{doc_id}",
    response_model=SummarizeResponse,
    summary="Generate document summary",
)
async def summarize_document(
    doc_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),  # noqa: ARG001
) -> SummarizeResponse:
    """Generate or regenerate a document summary."""
    repo = DocumentRepository(session)
    doc = await repo.get_by_id(doc_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    try:
        validate_transition(doc.status, "summarized")
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not doc.parsed_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has no parsed content",
        )

    from pathlib import Path

    import aiofiles

    path = Path(doc.parsed_path)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parsed content file not found",
        )

    async with aiofiles.open(path, "r") as f:
        content = await f.read()

    service = _get_summary_service()
    result = await service.generate_summary(doc_id, content)

    doc.status = "summarized"
    await session.flush()

    return SummarizeResponse(
        document_id=doc_id,
        summary=result["summary"],
        key_topics=result["key_topics"],
        status="summarized",
        cached=result["cached"],
    )


@router.get(
    "/summarize/{doc_id}",
    response_model=SummaryGetResponse,
    summary="Get existing summary",
)
async def get_summary(
    doc_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),  # noqa: ARG001
) -> SummaryGetResponse:
    """Get an existing document summary."""
    repo = DocumentRepository(session)
    doc = await repo.get_by_id(doc_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    service = _get_summary_service()
    cached = service.get_cached_summary(doc_id)
    if cached is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No summary exists for this document",
        )

    return SummaryGetResponse(
        document_id=doc_id,
        summary=cached["summary"],
        key_topics=cached["key_topics"],
        content_hash=cached["content_hash"],
    )
