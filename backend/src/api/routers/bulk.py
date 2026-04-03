"""Bulk processing API endpoints: upload, list jobs, get job details."""

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_app_settings, get_current_user_id, get_session
from src.api.routers.documents import MAX_FILE_SIZE, _validate_magic_bytes
from src.api.schemas.bulk import (
    BulkJobDetailResponse,
    BulkJobDocumentResponse,
    BulkJobListResponse,
    BulkJobResponse,
    BulkUploadResponse,
)
from src.bulk.service import BulkJobService
from src.db.connection import get_session_factory
from src.db.repositories.categories import CategoryRepository
from src.db.repositories.extraction import ExtractionFieldRepository, ExtractionSchemaRepository

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_EXTENSIONS = {"pdf", "docx", "xlsx", "png", "jpg", "tiff"}


def _extract_extension(filename: str) -> str:
    if "." in filename:
        return filename.rsplit(".", 1)[-1].lower()
    return ""


async def _run_pipeline_background(job_id: uuid.UUID) -> None:
    """Background task: load categories/fields and run pipeline."""
    factory = get_session_factory()
    async with factory() as session:
        cat_repo = CategoryRepository(session)
        categories = await cat_repo.list_all()
        cat_dicts = [
            {"id": c.id, "name": c.name, "classification_criteria": c.classification_criteria}
            for c in categories
        ]

        # Build extraction fields map per category
        schema_repo = ExtractionSchemaRepository(session)
        field_repo = ExtractionFieldRepository(session)
        extraction_fields_map: dict[str, list[dict]] = {}
        for cat in categories:
            schema = await schema_repo.get_latest_for_category(cat.id)
            if schema:
                fields = await field_repo.get_fields_for_schema(schema.id)
                extraction_fields_map[str(cat.id)] = [
                    {
                        "field_id": f.id,
                        "field_name": f.field_name,
                        "display_name": f.display_name,
                        "description": f.description,
                        "data_type": f.data_type,
                        "examples": f.examples,
                        "required": f.required,
                    }
                    for f in fields
                ]

        service = BulkJobService(session)
        await service.start_pipeline(
            job_id=job_id,
            categories=cat_dicts,
            extraction_fields_map=extraction_fields_map,
        )


@router.post(
    "/bulk/upload",
    response_model=BulkUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a bulk processing job",
)
async def bulk_upload(
    files: list[UploadFile],
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> BulkUploadResponse:
    """Upload multiple files and start bulk processing in the background."""
    if not files:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No files provided"
        )

    settings = get_app_settings()
    file_names: list[str] = []
    file_contents: list[bytes] = []
    file_types: list[str] = []

    for f in files:
        filename = f.filename or "unknown"
        ext = _extract_extension(filename)
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"File type '{ext}' not allowed for '{filename}'",
            )
        content = await f.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File '{filename}' exceeds max size",
            )
        if not _validate_magic_bytes(f".{ext}", content):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{filename}' content doesn't match format",
            )

        file_names.append(filename)
        file_contents.append(content)
        file_types.append(ext)

    service = BulkJobService(session)
    logger.info("Creating bulk job with %d files", len(file_names))
    job, documents = await service.create_job(
        file_names, file_contents, file_types,
        upload_dir=settings.storage.upload_dir,
        user_id=user_id,
    )
    logger.info("Bulk job %s created, starting background pipeline", job.id)

    # Start pipeline in background
    background_tasks.add_task(_run_pipeline_background, job.id)

    doc_responses = [
        BulkJobDocumentResponse(document_id=doc.id, file_name=doc.file_name, status="pending")
        for doc in documents
    ]
    return BulkUploadResponse(
        job_id=job.id,
        status=job.status,
        total_documents=job.total_documents,
        documents=doc_responses,
        created_at=job.created_at,
    )


@router.get("/bulk/jobs", response_model=BulkJobListResponse, summary="List bulk jobs")
async def list_bulk_jobs(
    status_filter: str | None = None,
    session: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> BulkJobListResponse:
    service = BulkJobService(session)
    jobs = await service.list_jobs(status=status_filter, user_id=user_id)
    return BulkJobListResponse(
        jobs=[
            BulkJobResponse(
                id=j.id, status=j.status, total_documents=j.total_documents,
                processed_count=j.processed_count, failed_count=j.failed_count,
                created_at=j.created_at, completed_at=j.completed_at,
            )
            for j in jobs
        ]
    )


@router.get("/bulk/jobs/{job_id}", response_model=BulkJobDetailResponse, summary="Get job details")
async def get_bulk_job(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> BulkJobDetailResponse:
    service = BulkJobService(session)
    job = await service.get_job(job_id, user_id=user_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    doc_responses = [
        BulkJobDocumentResponse(
            document_id=doc.document_id,
            file_name=doc.document.file_name if doc.document else "unknown",
            status=doc.status,
            error_message=doc.error_message,
            processing_time_ms=doc.processing_time_ms,
        )
        for doc in job.documents
    ]
    return BulkJobDetailResponse(
        id=job.id, status=job.status, total_documents=job.total_documents,
        processed_count=job.processed_count, failed_count=job.failed_count,
        created_at=job.created_at, completed_at=job.completed_at,
        documents=doc_responses,
    )
