"""FastAPI application factory with CORS middleware and lifespan management."""

import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.routes import register_routers
from src.api.seed_data import DEFAULT_CATEGORIES, LPA_EXTRACTION_FIELDS  # noqa: F401
from src.db.connection import dispose_engine, get_session_factory, init_engine

logger = logging.getLogger(__name__)
request_logger = logging.getLogger("src.api.requests")


async def _seed_default_categories() -> None:
    """Seed default PE document categories and LPA extraction fields."""
    try:
        factory = get_session_factory()
        async with factory() as session:
            from src.db.repositories.categories import CategoryRepository
            from src.db.repositories.extraction import (
                ExtractionFieldRepository,
                ExtractionSchemaRepository,
            )

            repo = CategoryRepository(session)
            count = await repo.count()
            if count == 0:
                for cat in DEFAULT_CATEGORIES:
                    await repo.create(
                        name=cat["name"],  # type: ignore[arg-type]
                        description=cat["description"],
                        classification_criteria=cat["classification_criteria"],
                    )
                await session.flush()
                logger.info("Seeded %d default document categories", len(DEFAULT_CATEGORIES))

            # Seed LPA extraction fields if none exist
            # Match flexibly — the name may be "Limited Partnership Agreement"
            # or "Limited Partnership Agreement - LPA" etc.
            all_cats = await repo.list_all()
            lpa_cat = next(
                (c for c in all_cats if "limited partnership" in c.name.lower()),
                None,
            )
            if lpa_cat is not None:
                schema_repo = ExtractionSchemaRepository(session)
                existing = await schema_repo.get_latest_for_category(lpa_cat.id)
                if existing is None:
                    schema = await schema_repo.create(category_id=lpa_cat.id, version=1)
                    field_repo = ExtractionFieldRepository(session)
                    for f in LPA_EXTRACTION_FIELDS:
                        await field_repo.upsert_field(
                            schema_id=schema.id,
                            field_name=f["field_name"],  # type: ignore[arg-type]
                            display_name=f["display_name"],  # type: ignore[arg-type]
                            description=f["description"],  # type: ignore[arg-type]
                            examples=f["examples"],  # type: ignore[arg-type]
                            data_type=f["data_type"],  # type: ignore[arg-type]
                            required=f["required"],  # type: ignore[arg-type]
                            sort_order=f["sort_order"],  # type: ignore[arg-type]
                        )
                    logger.info("Seeded %d LPA extraction fields", len(LPA_EXTRACTION_FIELDS))

            await session.commit()
    except Exception:
        logger.warning("Could not seed default categories (DB may not be ready)")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request with method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
        request_logger.log(
            log_level,
            "%s %s -> %d (%.0fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan handler: initialize DB pool on startup, dispose on shutdown."""
    database_url = app.state.database_url
    if database_url:
        from src.config.settings import get_settings as _get_settings

        _settings = _get_settings()
        logger.info("Initializing database connection pool")
        init_engine(
            database_url,
            pool_size=_settings.db_pool_size,
            max_overflow=_settings.db_max_overflow,
        )
        await _seed_default_categories()

        # Start audit queue background writer
        from src.audit import get_audit_queue

        audit_queue = get_audit_queue()
        audit_queue.start(
            database_url,
            pool_size=_settings.audit_pool_size,
            max_overflow=_settings.audit_max_overflow,
        )
    yield
    # Graceful shutdown: wake long-lived handlers (SSE), flush audit events.
    from src.api.shutdown import trigger_shutdown
    from src.audit import get_audit_queue as _get_aq

    trigger_shutdown()
    _get_aq().stop()
    logger.info("Shutting down, disposing database connections")
    await dispose_engine()


def create_app(database_url: str = "") -> FastAPI:
    """Create and configure a FastAPI application.

    Args:
        database_url: PostgreSQL async connection URL. If empty, the app
            starts without database initialization (useful for testing).

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="PE Document Intelligence Platform",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Store database URL in app state for the lifespan handler
    app.state.database_url = database_url

    # Request logging middleware (added first so it wraps everything)
    app.add_middleware(RequestLoggingMiddleware)

    # Correlation IDs + optional OpenTelemetry export to Phoenix / OTel collector
    from src.config.settings import get_settings
    from src.observability.tracing import CorrelationIdMiddleware, init_tracing

    settings = get_settings()
    app.add_middleware(CorrelationIdMiddleware)
    if settings.otel_enabled:
        init_tracing(
            app,
            service_name=settings.otel_service_name,
            endpoint=settings.otel_exporter_endpoint,
        )

    # CORS middleware allowing localhost origins for frontend dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_routers(app)

    return app
