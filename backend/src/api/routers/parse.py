"""Parse API endpoints: trigger parse, get content, save edits."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_app_settings, get_session
from src.api.schemas.parse import (
    EditContentRequest,
    EditContentResponse,
    ParseContentResponse,
    ParseResponse,
)
from src.db.repositories.documents import DocumentRepository
from src.parser.reducto import ReductoClient, ReductoParseError
from src.services.parse_service import ParseService
from src.services.state_machine import InvalidTransitionError
from src.storage.local import LocalStorage

router = APIRouter()


def _build_parse_service(
    session: AsyncSession,
) -> ParseService:
    """Build a ParseService from application settings."""
    settings = get_app_settings()
    repo = DocumentRepository(session)
    storage = LocalStorage(
        upload_dir=settings.storage.upload_dir,
        parsed_dir=settings.storage.parsed_dir,
    )
    reducto = ReductoClient(api_key=settings.reducto_api_key)
    return ParseService(repo=repo, storage=storage, reducto_client=reducto)


@router.post(
    "/parse/{doc_id}",
    response_model=ParseResponse,
    summary="Parse a document",
)
async def parse_document(
    doc_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> ParseResponse:
    """Trigger document parsing via Reducto."""
    service = _build_parse_service(session)
    try:
        doc, content, skipped = await service.parse_document(doc_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except InvalidTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except ReductoParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ParseResponse(
        document_id=doc.id,
        status=doc.status,
        content=content,
        skipped=skipped,
        message=(
            "File hash unchanged, returning cached parse result"
            if skipped
            else None
        ),
    )


@router.get(
    "/parse/{doc_id}/content",
    response_model=ParseContentResponse,
    summary="Get parsed content",
)
async def get_parsed_content(
    doc_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> ParseContentResponse:
    """Get parsed markdown content for a document."""
    service = _build_parse_service(session)
    repo = DocumentRepository(session)
    doc = await repo.get_by_id(doc_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    content = await service.get_parsed_content(doc_id)
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No parsed content exists",
        )

    return ParseContentResponse(
        document_id=doc.id, content=content, status=doc.status
    )


@router.put(
    "/parse/{doc_id}/content",
    response_model=EditContentResponse,
    summary="Save edited content",
)
async def save_edited_content(
    doc_id: uuid.UUID,
    body: EditContentRequest,
    session: AsyncSession = Depends(get_session),
) -> EditContentResponse:
    """Save edited markdown content."""
    service = _build_parse_service(session)
    try:
        doc = await service.save_edited_content(doc_id, body.content)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except InvalidTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return EditContentResponse(
        document_id=doc.id,
        status=doc.status,
        content_length=len(body.content),
    )
