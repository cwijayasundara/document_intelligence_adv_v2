"""Shared Pydantic schemas for API responses."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response schema for the health check endpoint."""

    model_config = {"exclude_none": True}

    status: str = Field(..., description="Health status: 'healthy' or 'unhealthy'")
    detail: str | None = Field(None, description="Error detail when unhealthy")


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    detail: str = Field(..., description="Human-readable error message")
    error_code: str | None = Field(None, description="Machine-readable error code")
    context: dict[str, object] | None = Field(None, description="Additional error context")
