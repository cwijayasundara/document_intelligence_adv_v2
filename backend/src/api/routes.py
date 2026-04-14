"""Router registration for the FastAPI application."""

from fastapi import FastAPI

from src.api.routers import (
    audit,
    bulk,
    classify,
    config,
    data_agent,
    documents,
    events,
    extract,
    health,
    ingest,
    parse,
    pipeline,
    rag,
    stream,
    summarize,
)


def register_routers(app: FastAPI) -> None:
    """Register all API routers with /api/v1 prefix."""
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
    app.include_router(stream.router, prefix="/api/v1", tags=["stream"])
    app.include_router(audit.router, prefix="/api/v1", tags=["audit"])
    app.include_router(events.router, prefix="/api/v1", tags=["events"])
    app.include_router(data_agent.router, prefix="/api/v1", tags=["analytics"])
    app.include_router(pipeline.router, prefix="/api/v1", tags=["pipeline"])
