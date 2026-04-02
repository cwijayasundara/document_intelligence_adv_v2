"""Structured output schema for the classifier subagent."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class ClassificationResult(BaseModel):
    """Result of document classification."""

    category_id: uuid.UUID = Field(..., description="UUID of the matched category")
    category_name: str = Field(..., description="Name of the matched category")
    confidence: int = Field(
        ...,
        ge=0,
        le=100,
        description="Confidence score 0-100 for the classification",
    )
    reasoning: str = Field(..., description="Explanation of why this category was chosen")
