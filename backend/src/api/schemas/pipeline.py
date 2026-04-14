"""Request/response schemas for the pipeline API."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class PipelineStartRequest(BaseModel):
    """Request body for starting a pipeline."""

    auto_pipeline: bool = Field(
        default=True,
        description="Start pipeline automatically after upload",
    )


class NodeStatusDetail(BaseModel):
    """Status of a single pipeline node."""

    status: str = Field(description="not_started, running, completed, failed, awaiting_review")
    started_at: str | None = Field(default=None)
    completed_at: str | None = Field(default=None)
    error: str | None = Field(default=None)


class PipelineStatusResponse(BaseModel):
    """Response for pipeline status queries."""

    document_id: uuid.UUID
    overall_status: str
    node_statuses: dict[str, NodeStatusDetail] = Field(default_factory=dict)
    node_timings: dict[str, float] = Field(default_factory=dict)
    next_nodes: list[str] = Field(default_factory=list)


class PipelineResumeRequest(BaseModel):
    """Request body for resuming a paused pipeline."""

    approved: bool = Field(default=True)
    data: dict[str, Any] = Field(default_factory=dict)


class PipelineRetryResponse(BaseModel):
    """Response after retrying a node."""

    document_id: uuid.UUID
    retried_node: str
    status: str
