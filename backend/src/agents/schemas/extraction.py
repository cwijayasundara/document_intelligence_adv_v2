"""Structured output schemas for extractor and judge subagents."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractedField(BaseModel):
    """A single extracted field value."""

    field_name: str = Field(..., description="Name of the extraction field")
    extracted_value: str = Field(
        ..., description="The value extracted from the document"
    )
    source_text: str = Field(
        ..., description="Source text from the document supporting this value"
    )


class ExtractionResult(BaseModel):
    """Result of field extraction from a document."""

    fields: list[ExtractedField] = Field(
        default_factory=list,
        description="List of extracted field values",
    )


class FieldEvaluation(BaseModel):
    """Confidence evaluation for a single extracted field."""

    field_name: str = Field(..., description="Name of the evaluated field")
    confidence: str = Field(
        ..., description="Confidence level: high, medium, or low"
    )
    reasoning: str = Field(
        ..., description="Explanation for the confidence rating"
    )


class JudgeResult(BaseModel):
    """Result of judge evaluation on extraction results."""

    evaluations: list[FieldEvaluation] = Field(
        default_factory=list,
        description="Confidence evaluations per field",
    )
