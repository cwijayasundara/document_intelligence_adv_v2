"""Health check endpoint verifying database connectivity."""

from fastapi import APIRouter, Response
from sqlalchemy import text

from src.api.schemas.common import HealthResponse
from src.db.connection import get_session_factory

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse}},
    summary="Health check",
    description="Check backend and database connectivity.",
)
async def health_check(response: Response) -> HealthResponse:
    """Return health status based on database connectivity."""
    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        return HealthResponse(status="healthy")
    except Exception as exc:
        response.status_code = 503
        return HealthResponse(status="unhealthy", detail=str(exc))
