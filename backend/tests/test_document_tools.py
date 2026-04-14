"""Tests for placeholder document tools."""

from src.graph_nodes.tools.document_tools import (
    get_document_status,
    get_parsed_content,
    list_documents,
)


async def test_get_parsed_content() -> None:
    """get_parsed_content returns stub data."""
    result = await get_parsed_content("doc-123")
    assert result["document_id"] == "doc-123"
    assert result["status"] == "stub"


async def test_get_document_status() -> None:
    """get_document_status returns stub data."""
    result = await get_document_status("doc-456")
    assert result["document_id"] == "doc-456"
    assert result["status"] == "stub"


async def test_list_documents() -> None:
    """list_documents returns empty stub."""
    result = await list_documents()
    assert result["documents"] == []
    assert result["total"] == 0
