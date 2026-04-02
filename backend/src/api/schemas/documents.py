"""Pydantic schemas for document API endpoints."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


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
    category_name: str | None = None
    file_type: str
    file_size: int
    parse_confidence_pct: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def _resolve_category_name(cls, data: Any) -> Any:
        """Extract category name from the ORM relationship."""
        if hasattr(data, "category") and data.category is not None:
            # ORM model — pull name from the related object
            data.__dict__["category_name"] = data.category.name
        return data


class DocumentListResponse(BaseModel):
    """Response schema for document list endpoint."""

    documents: list[DocumentListItem] = Field(default_factory=list)
    total: int = 0
