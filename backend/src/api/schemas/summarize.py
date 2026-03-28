"""Pydantic schemas for summarize API endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SummarizeResponse(BaseModel):
    """Response after generating a summary."""

    document_id: uuid.UUID
    summary: str
    key_topics: list[str] = Field(default_factory=list)
    status: str = "summarized"
    cached: bool = False


class SummaryGetResponse(BaseModel):
    """Response for getting an existing summary."""

    document_id: uuid.UUID
    summary: str
    key_topics: list[str] = Field(default_factory=list)
    content_hash: str
    created_at: datetime | None = None
