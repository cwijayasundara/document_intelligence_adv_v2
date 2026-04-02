"""Pydantic schemas for classification API endpoints."""

import uuid

from pydantic import BaseModel


class ClassifyResponse(BaseModel):
    """Response after classifying a document."""

    document_id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    confidence: int
    reasoning: str
    status: str = "classified"
