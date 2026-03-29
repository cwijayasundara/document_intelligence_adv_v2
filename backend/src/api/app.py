"""FastAPI application factory with CORS middleware and lifespan management."""

import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.routers import (
    bulk,
    classify,
    config,
    documents,
    extract,
    health,
    ingest,
    parse,
    rag,
    summarize,
)
from src.db.connection import dispose_engine, get_session_factory, init_engine

logger = logging.getLogger(__name__)
request_logger = logging.getLogger("src.api.requests")


async def _seed_default_category() -> None:
    """Seed the default 'Other/Unclassified' category if no categories exist."""
    try:
        factory = get_session_factory()
        async with factory() as session:
            from src.db.repositories.categories import CategoryRepository

            repo = CategoryRepository(session)
            count = await repo.count()
            if count == 0:
                await repo.create(
                    name="Other/Unclassified",
                    description="Default category for unclassified documents",
                    classification_criteria=None,
                )
                await session.commit()
                logger.info("Seeded default 'Other/Unclassified' category")
    except Exception:
        logger.warning("Could not seed default category (DB may not be ready)")


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
        logger.info("Initializing database connection pool")
        init_engine(database_url)
        await _seed_default_category()
    yield
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

    # Include routers with /api/v1 prefix
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
    app.include_router(config.router, prefix="/api/v1", tags=["config"])
    app.include_router(parse.router, prefix="/api/v1", tags=["parse"])
    app.include_router(summarize.router, prefix="/api/v1", tags=["summarize"])
    app.include_router(ingest.router, prefix="/api/v1", tags=["ingest"])
    app.include_router(classify.router, prefix="/api/v1", tags=["classify"])
    app.include_router(extract.router, prefix="/api/v1", tags=["extract"])
    app.include_router(rag.router, prefix="/api/v1", tags=["rag"])
    app.include_router(bulk.router, prefix="/api/v1", tags=["bulk"])

    return app
