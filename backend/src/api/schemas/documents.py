"""Pydantic schemas for document API endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """Response schema for a single document."""

    id: uuid.UUID
    file_name: str
    original_path: str
    parsed_path: str | None = None
    file_hash: str
    status: str
    document_category_id: uuid.UUID | None = None
    file_type: str
    file_size: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListItem(BaseModel):
    """Abbreviated document for list responses."""

    id: uuid.UUID
    file_name: str
    status: str
    document_category_id: uuid.UUID | None = None
    file_type: str
    file_size: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Response schema for document list endpoint."""

    documents: list[DocumentListItem] = Field(default_factory=list)
    total: int = 0
