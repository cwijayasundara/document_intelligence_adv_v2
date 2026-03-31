"""Ingest API endpoints for Weaviate ingestion."""

import logging
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from src.api.dependencies import get_app_settings, get_current_user_id, get_session
from src.db.repositories.documents import DocumentRepository
from src.rag.chunker import SemanticChunker
from src.rag.weaviate_client import COLLECTION_NAME, WeaviateClient
from src.services.ingest_service import IngestionService
from src.services.state_machine import InvalidTransitionError, validate_transition

router = APIRouter()


class IngestResponse(BaseModel):
    """Response after ingesting a document."""

    document_id: uuid.UUID
    status: str
    chunks_created: int
    collection: str


@router.post(
    "/ingest/{doc_id}",
    response_model=IngestResponse,
    summary="Ingest document into Weaviate",
)
async def ingest_document(
    doc_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),  # noqa: ARG001
) -> IngestResponse:
    """Chunk and ingest a document into Weaviate for RAG."""
    repo = DocumentRepository(session)
    doc = await repo.get_by_id(doc_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    try:
        validate_transition(doc.status, "ingested")
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

    settings = get_app_settings()
    weaviate = WeaviateClient(url=settings.weaviate_url)
    await weaviate.connect()

    chunker = SemanticChunker(
        max_tokens=settings.chunking.max_tokens,
        overlap_tokens=settings.chunking.overlap_tokens,
    )
    service = IngestionService(weaviate_client=weaviate, chunker=chunker)

    category_name = ""
    if doc.category:
        category_name = doc.category.name

    logger.info("Starting ingestion for document %s (%s)", doc_id, doc.file_name)
    chunks_created = await service.ingest_document(
        document_id=doc.id,
        document_name=doc.file_name,
        document_category=category_name,
        file_name=doc.file_name,
        parsed_content=content,
    )

    doc.status = "ingested"
    await session.flush()

    return IngestResponse(
        document_id=doc.id,
        status="ingested",
        chunks_created=chunks_created,
        collection=COLLECTION_NAME,
    )
