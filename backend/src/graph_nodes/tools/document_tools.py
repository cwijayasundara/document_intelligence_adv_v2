"""Placeholder document tools for the DeepAgent orchestrator.

These will be fully implemented in later stories (E2-S3, etc.).
"""

from typing import Any


async def get_parsed_content(document_id: str) -> dict[str, Any]:
    """Get parsed markdown content for a document. (Placeholder)."""
    return {"document_id": document_id, "content": "", "status": "stub"}


async def get_document_status(document_id: str) -> dict[str, Any]:
    """Get current status of a document. (Placeholder)."""
    return {"document_id": document_id, "status": "stub"}


async def list_documents() -> dict[str, Any]:
    """List all documents. (Placeholder)."""
    return {"documents": [], "total": 0}
