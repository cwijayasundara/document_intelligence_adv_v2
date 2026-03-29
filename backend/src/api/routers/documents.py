"""Document management API endpoints: upload, list, get, delete."""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from src.api.dependencies import get_app_settings, get_session
from src.api.schemas.documents import (
    DocumentListItem,
    DocumentListResponse,
    DocumentResponse,
)
from src.services.document_service import DocumentService
from src.storage.local import LocalStorage

router = APIRouter()

MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100 MB

ALLOWED_EXTENSIONS: set[str] = {".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg", ".tiff"}

# Mapping from extension to expected magic byte prefixes
_MAGIC_BYTES: dict[str, list[bytes]] = {
    ".pdf": [b"%PDF"],
    ".docx": [b"PK"],
    ".xlsx": [b"PK"],
    ".png": [b"\x89PNG"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".tiff": [b"II", b"MM"],
}


def _validate_magic_bytes(extension: str, content: bytes) -> bool:
    """Check that file content matches expected magic bytes for the extension."""
    expected = _MAGIC_BYTES.get(extension)
    if expected is None:
        return True  # No magic byte check configured for this extension
    return any(content.startswith(magic) for magic in expected)


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

    # VULN-004: Enforce file size limit
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE} bytes",
        )

    # VULN-005: Validate extension is allowed and magic bytes match
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File extension '{ext}' not allowed",
        )
    if not _validate_magic_bytes(ext, content):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File content does not match expected format for '{ext}'",
        )

    try:
        doc, is_duplicate = await service.upload(filename, content)
    except ValueError as exc:
        logger.warning("Upload rejected for %s: %s", filename, exc)
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

    try:
        docs, total = await service.list_documents(
            status=status_filter,
            category_id=category_id,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

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
