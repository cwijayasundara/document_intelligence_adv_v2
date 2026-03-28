"""Pydantic schemas for bulk processing API endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class BulkJobDocumentResponse(BaseModel):
    """Response schema for a single document within a bulk job."""

    document_id: uuid.UUID
    file_name: str
    status: str
    error_message: str | None = None
    processing_time_ms: int | None = None

    model_config = {"from_attributes": True}


class BulkJobResponse(BaseModel):
    """Response schema for bulk job list items."""

    id: uuid.UUID
    status: str
    total_documents: int
    processed_count: int
    failed_count: int
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class BulkJobDetailResponse(BaseModel):
    """Response schema for detailed bulk job view with document breakdown."""

    id: uuid.UUID
    status: str
    total_documents: int
    processed_count: int
    failed_count: int
    created_at: datetime
    completed_at: datetime | None = None
    documents: list[BulkJobDocumentResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class BulkUploadResponse(BaseModel):
    """Response schema for bulk upload endpoint."""

    job_id: uuid.UUID
    status: str
    total_documents: int
    documents: list[BulkJobDocumentResponse] = Field(default_factory=list)
    created_at: datetime


class BulkJobListResponse(BaseModel):
    """Response schema for listing all bulk jobs."""

    jobs: list[BulkJobResponse] = Field(default_factory=list)
