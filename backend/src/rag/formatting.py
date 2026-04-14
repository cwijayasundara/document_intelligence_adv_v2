"""Shared formatting utilities for RAG search results."""

from __future__ import annotations

from src.rag.weaviate_client import SearchResult


def format_chunk_context(chunk: SearchResult) -> str:
    """Format a search result chunk with header and section metadata."""
    header = f"[{chunk.document_name} — Chunk {chunk.chunk_index}]"
    meta_parts = []
    for key in ("header_1", "header_2", "header_3"):
        val = chunk.metadata.get(key)
        if val:
            meta_parts.append(val)
    section = f" ({' > '.join(meta_parts)})" if meta_parts else ""
    return f"{header}{section}\n{chunk.chunk_text}"


def format_chunks_as_context(chunks: list[SearchResult]) -> str:
    """Format multiple chunks into a single context string."""
    return "\n\n---\n\n".join(format_chunk_context(c) for c in chunks)


def build_citation(chunk: SearchResult) -> dict:
    """Build a citation dict from a search result."""
    section_parts = []
    for key in ("header_1", "header_2", "header_3"):
        val = chunk.metadata.get(key)
        if val:
            section_parts.append(val)
    return {
        "chunk_text": chunk.chunk_text,
        "document_name": chunk.document_name,
        "document_id": str(chunk.document_id),
        "chunk_index": chunk.chunk_index,
        "relevance_score": float(chunk.relevance_score),
        "section": " > ".join(section_parts),
    }
