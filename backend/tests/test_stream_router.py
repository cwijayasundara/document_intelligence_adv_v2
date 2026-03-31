"""Tests for SSE streaming router."""

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app
from src.api.routers import stream as stream_module
from src.bulk.event_bus import PipelineEventBus
from tests.db_helpers import TEST_BASE_URL


@pytest.fixture
def app_no_db():
    """Create app without database initialization."""
    return create_app(database_url="")


@pytest.fixture
async def client_no_db(app_no_db):
    """Create client for app without DB."""
    transport = ASGITransport(app=app_no_db)
    async with AsyncClient(transport=transport, base_url=TEST_BASE_URL) as ac:
        yield ac


class TestGetEventBus:
    """Test get_event_bus returns singleton."""

    def test_returns_pipeline_event_bus(self) -> None:
        # Reset singleton
        old = stream_module._event_bus
        stream_module._event_bus = None
        try:
            bus = stream_module.get_event_bus()
            assert isinstance(bus, PipelineEventBus)
        finally:
            stream_module._event_bus = old

    def test_returns_same_instance(self) -> None:
        old = stream_module._event_bus
        stream_module._event_bus = None
        try:
            bus1 = stream_module.get_event_bus()
            bus2 = stream_module.get_event_bus()
            assert bus1 is bus2
        finally:
            stream_module._event_bus = old


class TestStreamEndpoint:
    """Test SSE endpoint behaviour."""

    async def test_returns_event_stream_content_type(self, client_no_db: AsyncClient) -> None:
        """Endpoint should return text/event-stream media type."""
        job_id = "00000000-1111-2222-3333-444444444444"
        # Create a bus that will immediately send a job_completed event
        bus = PipelineEventBus()

        async def _fake_generator(jid, eb):  # type: ignore[no-untyped-def]
            yield 'data: {"type": "job_completed"}\n\n'

        with (
            patch.object(stream_module, "get_event_bus", return_value=bus),
            patch.object(stream_module, "_sse_generator", _fake_generator),
        ):
            response = await client_no_db.get(
                f"/api/v1/stream/jobs/{job_id}",
                headers={"X-User-Id": "test-user"},
            )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    async def test_requires_user_id_header(self, client_no_db: AsyncClient) -> None:
        """Endpoint should return 401 without X-User-Id."""
        job_id = "00000000-1111-2222-3333-444444444444"
        response = await client_no_db.get(
            f"/api/v1/stream/jobs/{job_id}",
        )
        assert response.status_code == 401
