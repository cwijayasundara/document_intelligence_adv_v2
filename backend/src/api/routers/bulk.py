"""Bulk processing API endpoints: upload, list jobs, get job details."""

import uuid
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_session
from src.api.routers.documents import MAX_FILE_SIZE, _validate_magic_bytes
from src.api.schemas.bulk import (
    BulkJobDetailResponse,
    BulkJobDocumentResponse,
    BulkJobListResponse,
    BulkJobResponse,
    BulkUploadResponse,
)
from src.bulk.service import BulkJobService

router = APIRouter()

ALLOWED_EXTENSIONS = {"pdf", "docx", "xlsx", "png", "jpg", "tiff"}


def _extract_extension(filename: str) -> str:
    """Extract file extension from filename."""
    if "." in filename:
        return filename.rsplit(".", 1)[-1].lower()
    return ""


@router.post(
    "/bulk/upload",
    response_model=BulkUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a bulk processing job",
)
async def bulk_upload(
    files: List[UploadFile],
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> BulkUploadResponse:
    """Upload multiple files and create a bulk processing job.

    Creates document records, a bulk_job, and starts pipeline
    processing in the background.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No files provided",
        )

    file_names: list[str] = []
    file_contents: list[bytes] = []
    file_types: list[str] = []

    for f in files:
        filename = f.filename or "unknown"
        ext = _extract_extension(filename)
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"File type '{ext}' not allowed for file '{filename}'",
            )
        content = await f.read()

        # Enforce file size limit
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File '{filename}' exceeds maximum allowed size of {MAX_FILE_SIZE} bytes",
            )

        # Validate magic bytes match the claimed extension
        ext_with_dot = f".{ext}"
        if not _validate_magic_bytes(ext_with_dot, content):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{filename}' content does not match expected format for '.{ext}'",
            )

        file_names.append(filename)
        file_contents.append(content)
        file_types.append(ext)

    service = BulkJobService(session)
    job, documents = await service.create_job(file_names, file_contents, file_types)

    # Build document response list using uploaded document info
    doc_responses = []
    for doc in documents:
        doc_responses.append(
            BulkJobDocumentResponse(
                document_id=doc.id,
                file_name=doc.file_name,
                status="pending",
            )
        )

    return BulkUploadResponse(
        job_id=job.id,
        status=job.status,
        total_documents=job.total_documents,
        documents=doc_responses,
        created_at=job.created_at,
    )


@router.get(
    "/bulk/jobs",
    response_model=BulkJobListResponse,
    summary="List all bulk jobs",
)
async def list_bulk_jobs(
    status_filter: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> BulkJobListResponse:
    """List all bulk jobs with optional status filter."""
    service = BulkJobService(session)
    jobs = await service.list_jobs(status=status_filter)

    job_responses = [
        BulkJobResponse(
            id=j.id,
            status=j.status,
            total_documents=j.total_documents,
            processed_count=j.processed_count,
            failed_count=j.failed_count,
            created_at=j.created_at,
            completed_at=j.completed_at,
        )
        for j in jobs
    ]

    return BulkJobListResponse(jobs=job_responses)


@router.get(
    "/bulk/jobs/{job_id}",
    response_model=BulkJobDetailResponse,
    summary="Get bulk job details",
)
async def get_bulk_job(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> BulkJobDetailResponse:
    """Get bulk job details with per-document breakdown."""
    service = BulkJobService(session)
    job = await service.get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bulk job not found",
        )

    doc_responses = []
    for doc in job.documents:
        doc_responses.append(
            BulkJobDocumentResponse(
                document_id=doc.document_id,
                file_name=(
                    doc.document.file_name
                    if hasattr(doc, "document") and doc.document
                    else "unknown"
                ),
                status=doc.status,
                error_message=doc.error_message,
                processing_time_ms=doc.processing_time_ms,
            )
        )

    return BulkJobDetailResponse(
        id=job.id,
        status=job.status,
        total_documents=job.total_documents,
        processed_count=job.processed_count,
        failed_count=job.failed_count,
        created_at=job.created_at,
        completed_at=job.completed_at,
        documents=doc_responses,
    )
