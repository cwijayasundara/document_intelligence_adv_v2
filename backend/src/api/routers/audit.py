"""Audit trail API endpoint for querying audit logs."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_session
from src.db.models.audit import AuditLog

router = APIRouter()


class AuditLogItem(BaseModel):
    """Single audit log entry."""

    id: uuid.UUID
    event_type: str
    entity_type: str
    entity_id: str | None = None
    document_id: str | None = None
    file_name: str | None = None
    details: dict | None = None
    error: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditTrailResponse(BaseModel):
    """Paginated audit trail response."""

    events: list[AuditLogItem] = Field(default_factory=list)
    total: int = 0


@router.get(
    "/audit/trail",
    response_model=AuditTrailResponse,
    summary="Query audit trail",
)
async def get_audit_trail(
    event_type: str | None = Query(None, description="Filter by event type"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    document_id: str | None = Query(None, description="Filter by document ID"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> AuditTrailResponse:
    """Query audit log events with optional filters."""
    from sqlalchemy import func

    stmt = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)

    if event_type:
        stmt = stmt.where(AuditLog.event_type == event_type)
        count_stmt = count_stmt.where(AuditLog.event_type == event_type)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
        count_stmt = count_stmt.where(AuditLog.entity_type == entity_type)
    if document_id:
        stmt = stmt.where(AuditLog.document_id == document_id)
        count_stmt = count_stmt.where(AuditLog.document_id == document_id)

    stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)

    result = await session.execute(stmt)
    logs = list(result.scalars().all())

    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    items = [AuditLogItem.model_validate(log) for log in logs]
    return AuditTrailResponse(events=items, total=total)
