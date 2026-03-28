"""Classification API endpoint: trigger classifier subagent."""

import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.classifier import ClassifierSubagent
from src.api.dependencies import get_session
from src.api.schemas.classify import ClassifyResponse
from src.db.repositories.categories import CategoryRepository
from src.db.repositories.documents import DocumentRepository
from src.services.state_machine import InvalidTransitionError, validate_transition

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
    session: AsyncSession = Depends(get_session),
) -> ClassifyResponse:
    """Trigger classification for a document via the classifier subagent."""
    repo = DocumentRepository(session)
    doc = await repo.get_by_id(doc_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

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
    result = await classifier.classify(content, cat_dicts)

    doc.document_category_id = result.category_id
    doc.status = "classified"
    await session.flush()

    return ClassifyResponse(
        document_id=doc_id,
        category_id=result.category_id,
        category_name=result.category_name,
        reasoning=result.reasoning,
        status="classified",
    )
