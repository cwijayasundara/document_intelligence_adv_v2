"""Pydantic schemas for category and extraction field configuration."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    """Request schema for creating a category."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    classification_criteria: str | None = None


class CategoryUpdate(BaseModel):
    """Request schema for updating a category."""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    classification_criteria: str | None = None


class CategoryResponse(BaseModel):
    """Response schema for a single category."""

    id: uuid.UUID
    name: str
    description: str | None = None
    classification_criteria: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CategoryListResponse(BaseModel):
    """Response schema for category list endpoint."""

    categories: list[CategoryResponse] = Field(default_factory=list)


class FieldCreate(BaseModel):
    """Request schema for a single extraction field."""

    field_name: str = Field(..., min_length=1, max_length=200)
    display_name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    examples: str | None = None
    data_type: str = "string"
    required: bool = False
    sort_order: int = 0


class FieldsCreateRequest(BaseModel):
    """Request schema for creating/updating extraction fields."""

    fields: list[FieldCreate] = Field(..., min_length=1)


class FieldResponse(BaseModel):
    """Response schema for a single extraction field."""

    id: uuid.UUID
    field_name: str
    display_name: str
    description: str | None = None
    examples: str | None = None
    data_type: str
    required: bool
    sort_order: int

    model_config = {"from_attributes": True}


class FieldsListResponse(BaseModel):
    """Response schema for extraction fields list."""

    category_id: uuid.UUID
    category_name: str
    schema_version: int
    fields: list[FieldResponse] = Field(default_factory=list)


class FieldsCreateResponse(BaseModel):
    """Response after creating/updating extraction fields."""

    category_id: uuid.UUID
    schema_version: int
    fields_created: int
    fields_updated: int
