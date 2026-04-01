"""Tests for OpenTelemetry tracing setup and correlation ID middleware."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.observability.tracing import (
    CorrelationIdMiddleware,
    get_tracer,
    init_tracing,
)


def _make_app() -> FastAPI:
    """Create a minimal FastAPI app with CorrelationIdMiddleware."""
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    return app


@pytest.fixture
def app() -> FastAPI:
    return _make_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_correlation_id_added_to_response(client: AsyncClient) -> None:
    """CorrelationIdMiddleware generates a correlation ID when none is sent."""
    response = await client.get("/ping")
    assert response.status_code == 200
    cid = response.headers.get("X-Correlation-Id")
    assert cid is not None
    # Should be a valid UUID
    uuid.UUID(cid)


async def test_correlation_id_preserved_when_sent(client: AsyncClient) -> None:
    """CorrelationIdMiddleware preserves an existing X-Correlation-Id header."""
    existing_id = "my-custom-correlation-id-123"
    response = await client.get("/ping", headers={"X-Correlation-Id": existing_id})
    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == existing_id


def test_get_tracer_returns_none_when_otel_unavailable() -> None:
    """get_tracer returns None when opentelemetry is not importable."""
    with patch.dict("sys.modules", {"opentelemetry": None, "opentelemetry.trace": None}):
        # Re-import won't help since function does dynamic import; mock builtins
        with patch("builtins.__import__", side_effect=ImportError("no otel")):
            result = get_tracer()
    assert result is None


def test_init_tracing_handles_import_error() -> None:
    """init_tracing logs a warning when opentelemetry packages are missing."""
    app = FastAPI()
    with patch("builtins.__import__", side_effect=ImportError("no otel")):
        # Should not raise
        init_tracing(app, service_name="test-svc", endpoint="http://localhost:4317")


def test_init_tracing_success() -> None:
    """init_tracing instruments the app when opentelemetry is available."""
    app = FastAPI()

    mock_trace = MagicMock()
    mock_resource_cls = MagicMock()
    mock_provider_cls = MagicMock()
    mock_instrumentor = MagicMock()

    modules = {
        "opentelemetry": MagicMock(trace=mock_trace),
        "opentelemetry.trace": mock_trace,
        "opentelemetry.sdk": MagicMock(),
        "opentelemetry.sdk.resources": MagicMock(Resource=mock_resource_cls),
        "opentelemetry.sdk.trace": MagicMock(TracerProvider=mock_provider_cls),
        "opentelemetry.instrumentation": MagicMock(),
        "opentelemetry.instrumentation.fastapi": MagicMock(FastAPIInstrumentor=mock_instrumentor),
    }

    with patch.dict("sys.modules", modules):
        init_tracing(app, service_name="test-svc", endpoint="http://localhost:4317")

    mock_resource_cls.create.assert_called_once_with({"service.name": "test-svc"})
    mock_provider_cls.assert_called_once()
    mock_trace.set_tracer_provider.assert_called_once()
    mock_instrumentor.instrument_app.assert_called_once_with(app)


def test_get_tracer_returns_tracer_when_available() -> None:
    """get_tracer returns a tracer when opentelemetry is importable."""
    mock_trace = MagicMock()
    mock_tracer = MagicMock()
    mock_trace.get_tracer.return_value = mock_tracer

    modules = {
        "opentelemetry": MagicMock(trace=mock_trace),
        "opentelemetry.trace": mock_trace,
    }

    with patch.dict("sys.modules", modules):
        result = get_tracer("my-service")

    mock_trace.get_tracer.assert_called_once_with("my-service")
    assert result is mock_tracer
