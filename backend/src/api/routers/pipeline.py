"""Pipeline API: start, resume, retry, and status for document pipelines."""

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user_id, get_session
from src.api.schemas.pipeline import (
    PipelineResumeRequest,
    PipelineRetryResponse,
    PipelineStatusResponse,
)
from src.db.repositories.categories import CategoryRepository
from src.db.repositories.documents import DocumentRepository
from src.db.repositories.extraction import (
    ExtractionFieldRepository,
    ExtractionSchemaRepository,
)
from src.pipeline.runner import PipelineRunner

logger = logging.getLogger(__name__)

router = APIRouter()

VALID_NODES = {"parse", "summarize", "classify", "extract", "ingest"}


async def _load_categories_and_fields(
    session: AsyncSession,
) -> tuple[list[dict], dict[str, list[dict]]]:
    """Load categories and extraction fields for pipeline init."""
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

    schema_repo = ExtractionSchemaRepository(session)
    field_repo = ExtractionFieldRepository(session)
    fields_map: dict[str, list[dict]] = {}
    for cat in categories:
        schema = await schema_repo.get_latest_for_category(cat.id)
        if schema is None:
            continue
        fields = await field_repo.get_fields_for_schema(schema.id)
        if fields:
            fields_map[str(cat.id)] = [
                {
                    "field_id": f.id,
                    "field_name": f.field_name,
                    "display_name": f.display_name,
                    "description": f.description,
                    "data_type": f.data_type,
                    "required": f.required,
                    "examples": f.examples,
                }
                for f in fields
            ]

    return cat_dicts, fields_map


async def _run_pipeline_bg(
    document_id: uuid.UUID,
    file_name: str,
    original_path: str,
    categories: list[dict],
    fields_map: dict[str, list[dict]],
) -> None:
    """Background task: run pipeline for a document."""
    runner = PipelineRunner()
    try:
        await runner.start(
            document_id=document_id,
            file_name=file_name,
            original_path=original_path,
            categories=categories,
            extraction_fields_map=fields_map,
        )
    except Exception as exc:
        logger.error(
            "[pipeline:%s] Background pipeline failed: %s",
            str(document_id)[:8],
            exc,
        )


@router.post("/pipeline/{doc_id}/start", summary="Start pipeline")
async def start_pipeline(
    doc_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Start the unified pipeline for a document."""
    repo = DocumentRepository(session)
    doc = await repo.get_by_id(doc_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    if doc.status == "processing":
        raise HTTPException(status.HTTP_409_CONFLICT, "Pipeline already running")

    categories, fields_map = await _load_categories_and_fields(session)

    background_tasks.add_task(
        _run_pipeline_bg,
        document_id=doc_id,
        file_name=doc.file_name,
        original_path=doc.original_path,
        categories=categories,
        fields_map=fields_map,
    )

    return {"document_id": doc_id, "status": "pipeline_started"}


@router.post("/pipeline/{doc_id}/resume", summary="Resume pipeline")
async def resume_pipeline(
    doc_id: uuid.UUID,
    body: PipelineResumeRequest | None = None,
    session: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Resume a paused pipeline after human review."""
    repo = DocumentRepository(session)
    doc = await repo.get_by_id(doc_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    if not doc.status.startswith("awaiting_"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Document is not paused (status={doc.status})",
        )

    runner = PipelineRunner()
    resume_data = body.data if body else {}
    result = await runner.resume(doc_id, resume_data=resume_data)

    return {
        "document_id": doc_id,
        "status": result.get("status", "unknown"),
    }


@router.post(
    "/pipeline/{doc_id}/retry/{node_name}",
    response_model=PipelineRetryResponse,
    summary="Retry a failed node",
)
async def retry_node(
    doc_id: uuid.UUID,
    node_name: str,
    session: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> PipelineRetryResponse:
    """Retry a specific failed pipeline node."""
    if node_name not in VALID_NODES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Invalid node: {node_name}. Valid: {VALID_NODES}",
        )

    repo = DocumentRepository(session)
    doc = await repo.get_by_id(doc_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    runner = PipelineRunner()
    try:
        result = await runner.retry_node(doc_id, node_name)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    return PipelineRetryResponse(
        document_id=doc_id,
        retried_node=node_name,
        status=result.get("status", "unknown"),
    )


@router.get(
    "/pipeline/{doc_id}/status",
    response_model=PipelineStatusResponse,
    summary="Get pipeline status",
)
async def get_pipeline_status(
    doc_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> PipelineStatusResponse:
    """Get per-node pipeline status for a document."""
    repo = DocumentRepository(session)
    doc = await repo.get_by_id(doc_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    runner = PipelineRunner()
    pipeline_state = await runner.get_status(doc_id)

    node_statuses = {}
    if doc.pipeline_node_status:
        for name, detail in doc.pipeline_node_status.items():
            from src.api.schemas.pipeline import NodeStatusDetail

            node_statuses[name] = NodeStatusDetail(**detail)

    return PipelineStatusResponse(
        document_id=doc_id,
        overall_status=doc.status,
        node_statuses=node_statuses,
        node_timings=pipeline_state.get("node_timings", {}) if pipeline_state else {},
        next_nodes=pipeline_state.get("next_nodes", []) if pipeline_state else [],
    )
