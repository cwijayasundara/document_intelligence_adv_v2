"""Tests for E1-S4: FastAPI Application Factory + Health Endpoint.

Verifies the app factory, CORS middleware, /api/v1 prefix, lifespan,
and health endpoint responses (200 healthy, 503 unhealthy).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app
from src.api.schemas.common import ErrorResponse, HealthResponse
import src.db.connection as conn_module


@pytest.fixture
def app_no_db():
    """Create app without database initialization."""
    return create_app(database_url="")


@pytest.fixture
async def client_no_db(app_no_db):
    """Create client for app without DB."""
    transport = ASGITransport(app=app_no_db)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestAppFactory:
    """Test create_app factory function."""

    def test_creates_fastapi_app(self) -> None:
        app = create_app(database_url="")
        assert app.title == "PE Document Intelligence Platform"

    def test_app_version(self) -> None:
        app = create_app(database_url="")
        assert app.version == "1.0.0"

    def test_stores_database_url_in_state(self) -> None:
        url = "postgresql+asyncpg://test:test@localhost:5432/test"
        app = create_app(database_url=url)
        assert app.state.database_url == url


class TestCORSMiddleware:
    """Test CORS configuration allows localhost origins."""

    async def test_cors_preflight_localhost_5173(self, client_no_db: AsyncClient) -> None:
        response = await client_no_db.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

    async def test_cors_preflight_localhost_3000(self, client_no_db: AsyncClient) -> None:
        response = await client_no_db.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


class TestAPIPrefix:
    """Test all routes use /api/v1 prefix."""

    async def test_health_at_api_v1_prefix(self, client_no_db: AsyncClient) -> None:
        # Health should be accessible at /api/v1/health (even if DB fails, it returns 503)
        response = await client_no_db.get("/api/v1/health")
        assert response.status_code in (200, 503)

    async def test_health_without_prefix_returns_404(self, client_no_db: AsyncClient) -> None:
        response = await client_no_db.get("/health")
        assert response.status_code == 404


class TestHealthEndpoint:
    """Test GET /api/v1/health responses."""

    async def test_healthy_when_db_reachable(self, app_no_db) -> None:
        """Mock database to return healthy status."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        mock_factory = MagicMock(return_value=mock_cm)

        with patch.object(conn_module, "_session_factory", mock_factory):
            transport = ASGITransport(app=app_no_db)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data.get("detail") is None

    async def test_unhealthy_when_db_unreachable(self, client_no_db: AsyncClient) -> None:
        """Without initialized DB, health endpoint should return 503."""
        # Reset module state to simulate uninitialized DB
        old_factory = conn_module._session_factory
        conn_module._session_factory = None
        try:
            response = await client_no_db.get("/api/v1/health")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["detail"] is not None
            assert len(data["detail"]) > 0
        finally:
            conn_module._session_factory = old_factory

    async def test_unhealthy_when_db_query_fails(self, app_no_db) -> None:
        """Mock database session that raises on execute."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("Connection refused"))

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        mock_factory = MagicMock(return_value=mock_cm)

        with patch.object(conn_module, "_session_factory", mock_factory):
            transport = ASGITransport(app=app_no_db)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.get("/api/v1/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "Connection refused" in data["detail"]


class TestHealthResponseSchema:
    """Test HealthResponse Pydantic schema."""

    def test_healthy_response(self) -> None:
        r = HealthResponse(status="healthy")
        assert r.status == "healthy"
        assert r.detail is None

    def test_unhealthy_response_with_detail(self) -> None:
        r = HealthResponse(status="unhealthy", detail="DB connection failed")
        assert r.status == "unhealthy"
        assert r.detail == "DB connection failed"


class TestErrorResponseSchema:
    """Test ErrorResponse Pydantic schema."""

    def test_error_response(self) -> None:
        r = ErrorResponse(detail="Not found", error_code="NOT_FOUND")
        assert r.detail == "Not found"
        assert r.error_code == "NOT_FOUND"

    def test_error_response_with_context(self) -> None:
        r = ErrorResponse(
            detail="Category in use",
            error_code="CATEGORY_IN_USE",
            context={"document_count": 5},
        )
        assert r.context == {"document_count": 5}
