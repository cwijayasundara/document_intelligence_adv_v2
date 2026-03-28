"""Pydantic schemas for parse API endpoints."""

import uuid

from pydantic import BaseModel


class ParseResponse(BaseModel):
    """Response after parsing a document."""

    document_id: uuid.UUID
    status: str
    content: str
    skipped: bool = False
    message: str | None = None


class ParseContentResponse(BaseModel):
    """Response for getting parsed content."""

    document_id: uuid.UUID
    content: str
    status: str


class EditContentRequest(BaseModel):
    """Request body for saving edited content."""

    content: str


class EditContentResponse(BaseModel):
    """Response after saving edited content."""

    document_id: uuid.UUID
    status: str
    content_length: int
