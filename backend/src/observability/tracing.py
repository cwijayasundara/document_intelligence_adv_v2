"""OpenTelemetry tracing setup and correlation ID middleware."""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


def init_tracing(app: FastAPI, service_name: str, endpoint: str = "") -> None:
    """Initialize OpenTelemetry tracing for the FastAPI app.

    When `endpoint` is set (e.g. `http://localhost:6006/v1/traces` for local
    Arize Phoenix, or an OTel collector URL), spans are batched and shipped
    via OTLP/HTTP. When empty, the tracer is still installed so in-process
    spans are observable, but nothing is exported.
    """
    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider

        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)

        if endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter,
                )
                from opentelemetry.sdk.trace.export import BatchSpanProcessor

                exporter = OTLPSpanExporter(endpoint=endpoint)
                provider.add_span_processor(BatchSpanProcessor(exporter))
                logger.info("OTLP exporter wired to %s", endpoint)
            except ImportError:
                logger.warning(
                    "OTLP exporter not installed; spans will not be exported. "
                    "Install opentelemetry-exporter-otlp-proto-http."
                )

        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        logger.info("OpenTelemetry tracing initialized for %s", service_name)
    except ImportError:
        logger.warning("OpenTelemetry packages not available, tracing disabled")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware that adds correlation IDs to requests."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        correlation_id = request.headers.get("X-Correlation-Id", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-Id"] = correlation_id
        return response


def get_tracer(name: str = "doc-intel"):
    """Get a tracer instance. Returns None if OTel is not configured."""
    try:
        from opentelemetry import trace

        return trace.get_tracer(name)
    except ImportError:
        return None
