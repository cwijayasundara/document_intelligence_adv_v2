"""RAG service orchestrating retrieval and answer generation."""

from __future__ import annotations

from typing import Any

from src.agents.rag_retriever import RAGRetrieverSubagent
from src.rag.weaviate_client import WeaviateClient

SEARCH_MODE_ALPHA = {
    "keyword": 0.0,
    "hybrid": 0.5,
    "semantic": 1.0,
}


class RAGService:
    """Orchestrate RAG retrieval and answer generation."""

    def __init__(self, weaviate_client: WeaviateClient) -> None:
        self._weaviate = weaviate_client
        self._retriever = RAGRetrieverSubagent(weaviate_client)

    async def query(
        self,
        query: str,
        scope: str,
        scope_id: str | None = None,
        search_mode: str = "hybrid",
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Execute a RAG query with scope filtering.

        Args:
            query: User's question.
            scope: single_document, all, or by_category.
            scope_id: Document or category ID for filtering.
            search_mode: semantic, keyword, or hybrid.
            top_k: Number of chunks to retrieve.

        Returns:
            Dict with answer, citations, search_mode, chunks_retrieved.
        """
        alpha = SEARCH_MODE_ALPHA.get(search_mode, 0.5)
        doc_id = scope_id if scope == "single_document" else None
        category = scope_id if scope == "by_category" else None

        chunks = await self._retriever.retrieve(
            query=query,
            top_k=top_k,
            document_id=doc_id,
            category_filter=category,
            alpha=alpha,
        )

        answer = await self._retriever.generate_answer(query, chunks)

        citations = [
            {
                "chunk_text": c.chunk_text,
                "document_name": c.document_name,
                "document_id": c.document_id,
                "chunk_index": c.chunk_index,
                "relevance_score": c.relevance_score,
            }
            for c in chunks
        ]

        return {
            "answer": answer,
            "citations": citations,
            "search_mode": search_mode,
            "chunks_retrieved": len(chunks),
        }
