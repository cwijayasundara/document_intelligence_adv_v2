"""Data analytics agent API endpoint."""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_session
from src.data_agent.agent import DataAgent

logger = logging.getLogger(__name__)

router = APIRouter()

_agent: DataAgent | None = None


def _get_agent() -> DataAgent:
    global _agent
    if _agent is None:
        _agent = DataAgent()
    return _agent


class AnalyticsQueryRequest(BaseModel):
    question: str = Field(..., description="Natural language question")


class ChartConfigResponse(BaseModel):
    chart_type: str = "table"
    title: str = ""
    x_key: str = ""
    y_key: str = ""
    name_key: str = ""
    value_key: str = ""


class AnalyticsQueryResponse(BaseModel):
    sql: str = ""
    data: dict = Field(default_factory=dict)
    chart: ChartConfigResponse = Field(default_factory=ChartConfigResponse)
    explanation: str = ""
    error: str | None = None


@router.post(
    "/analytics/query",
    response_model=AnalyticsQueryResponse,
    summary="Ask analytics question",
)
async def analytics_query(
    body: AnalyticsQueryRequest,
    session: AsyncSession = Depends(get_session),
) -> AnalyticsQueryResponse:
    """Convert a natural language question to SQL, execute, and return chart data."""
    logger.info("Analytics query: %s", body.question[:100])
    agent = _get_agent()
    result = await agent.query(body.question, session)

    from src.audit import emit_audit_event

    emit_audit_event(
        event_type="analytics.query",
        entity_type="analytics",
        details={
            "question": body.question,
            "sql": result.get("sql", ""),
            "rows_returned": len(result.get("data", {}).get("rows", [])),
        },
    )

    return AnalyticsQueryResponse(
        sql=result.get("sql", ""),
        data=result.get("data", {}),
        chart=ChartConfigResponse(**result.get("chart", {})),
        explanation=result.get("explanation", ""),
        error=result.get("error"),
    )
