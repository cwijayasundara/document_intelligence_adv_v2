"""Structured output schema for the summarizer subagent."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SummaryResult(BaseModel):
    """Result of document summarization."""

    summary: str = Field(..., description="Document summary text")
    key_topics: list[str] = Field(
        default_factory=list,
        description="Key topics identified in the document",
    )
