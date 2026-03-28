"""FastAPI application factory with CORS middleware and lifespan management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import health
from src.db.connection import dispose_engine, init_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan handler: initialize DB pool on startup, dispose on shutdown."""
    database_url = app.state.database_url
    init_engine(database_url)
    yield
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

    return app
