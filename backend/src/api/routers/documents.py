"""Document management API endpoints: upload, list, get, delete."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_app_settings, get_session
from src.api.schemas.documents import (
    DocumentListResponse,
    DocumentListItem,
    DocumentResponse,
)
from src.services.document_service import DocumentService
from src.storage.local import LocalStorage

router = APIRouter()


def _get_storage() -> LocalStorage:
    """Build a LocalStorage from application settings."""
    settings = get_app_settings()
    return LocalStorage(
        upload_dir=settings.storage.upload_dir,
        parsed_dir=settings.storage.parsed_dir,
    )


@router.post(
    "/documents/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
)
async def upload_document(
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
) -> DocumentResponse:
    """Upload a document file with SHA-256 dedup."""
    storage = _get_storage()
    service = DocumentService(session, storage)

    content = await file.read()
    filename = file.filename or "unknown"

    try:
        doc, is_duplicate = await service.upload(filename, content)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    response = DocumentResponse.model_validate(doc)

    if is_duplicate:
        # Return 200 for duplicates instead of 201
        return response  # FastAPI will use the route default 201; override below

    return response


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List all documents",
)
async def list_documents(
    status_filter: str | None = None,
    category_id: uuid.UUID | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    session: AsyncSession = Depends(get_session),
) -> DocumentListResponse:
    """List all documents with optional filtering and sorting."""
    storage = _get_storage()
    service = DocumentService(session, storage)

    docs, total = await service.list_documents(
        status=status_filter,
        category_id=category_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    items = [DocumentListItem.model_validate(d) for d in docs]
    return DocumentListResponse(documents=items, total=total)


@router.get(
    "/documents/{doc_id}",
    response_model=DocumentResponse,
    summary="Get document details",
)
async def get_document(
    doc_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> DocumentResponse:
    """Get full document details by ID."""
    storage = _get_storage()
    service = DocumentService(session, storage)

    doc = await service.get_document(doc_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return DocumentResponse.model_validate(doc)


@router.delete(
    "/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
async def delete_document(
    doc_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a document and its associated files."""
    storage = _get_storage()
    service = DocumentService(session, storage)

    deleted = await service.delete_document(doc_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
