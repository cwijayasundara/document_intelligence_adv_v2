"""Pydantic schemas for RAG query API endpoints."""

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """A citation referencing a document chunk."""

    chunk_text: str
    document_name: str
    document_id: str
    chunk_index: int = 0
    relevance_score: float = 0.0
    section: str = ""


class RAGQueryRequest(BaseModel):
    """Request body for RAG query endpoint."""

    query: str
    scope: str = Field(..., description="single_document, all, or by_category")
    scope_id: str | None = Field(
        default=None,
        description="Document ID or category ID for scope filtering",
    )
    search_mode: str = Field(
        default="hybrid",
        description="semantic, keyword, or hybrid",
    )
    top_k: int = Field(default=5, ge=1, le=50)


class RAGQueryResponse(BaseModel):
    """Response from RAG query endpoint."""

    answer: str
    citations: list[Citation] = Field(default_factory=list)
    search_mode: str = "hybrid"
    chunks_retrieved: int = 0
