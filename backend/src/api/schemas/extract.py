"""Pydantic schemas for extraction API endpoints."""

import uuid

from pydantic import BaseModel, Field


class ExtractionResultItem(BaseModel):
    """A single extraction result."""

    id: uuid.UUID
    field_name: str
    display_name: str
    extracted_value: str | None = None
    source_text: str | None = None
    confidence: str
    confidence_reasoning: str | None = None
    requires_review: bool = False
    reviewed: bool = False


class ExtractionResponse(BaseModel):
    """Response after running extraction."""

    document_id: uuid.UUID
    status: str = "extracted"
    results: list[ExtractionResultItem] = Field(default_factory=list)
    requires_review_count: int = 0


class ExtractionResultsResponse(BaseModel):
    """Response for GET extraction results."""

    document_id: uuid.UUID
    results: list[ExtractionResultItem] = Field(default_factory=list)
    requires_review_count: int = 0
    all_reviewed: bool = True


class FieldUpdate(BaseModel):
    """A single field update."""

    field_id: uuid.UUID
    extracted_value: str
    reviewed: bool = True


class ExtractionUpdateRequest(BaseModel):
    """Request to update extracted values."""

    updates: list[FieldUpdate]


class ExtractionUpdateResponse(BaseModel):
    """Response after updating extracted values."""

    document_id: uuid.UUID
    updated_count: int
    requires_review_count: int = 0
    all_reviewed: bool = True
    can_proceed: bool = True
