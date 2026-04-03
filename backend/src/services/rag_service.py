"""RAG service orchestrating retrieval and answer generation."""

from __future__ import annotations

import logging
from typing import Any

from src.agents.rag_retriever import RAGRetrieverSubagent
from src.rag.weaviate_client import WeaviateClient

logger = logging.getLogger(__name__)

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

        logger.info(
            "Retrieving chunks: query='%s', alpha=%.1f, doc_id=%s, category=%s, top_k=%d",
            query[:80],
            alpha,
            doc_id,
            category,
            top_k,
        )

        chunks = self._retriever.retrieve(
            query=query,
            top_k=top_k,
            document_id=doc_id,
            category_filter=category,
            alpha=alpha,
        )
        logger.info("Retrieved %d chunks from Weaviate", len(chunks))

        if not chunks:
            logger.warning("No chunks found for query: '%s'", query[:80])
            return {
                "answer": "No relevant content found in the selected documents.",
                "citations": [],
                "search_mode": search_mode,
                "chunks_retrieved": 0,
            }

        logger.info("Generating answer from %d chunks via LLM", len(chunks))
        answer = await self._retriever.generate_answer(query, chunks)

        citations = []
        for c in chunks:
            section_parts = []
            for key in ("header_1", "header_2", "header_3"):
                val = c.metadata.get(key)
                if val:
                    section_parts.append(val)
            citations.append({
                "chunk_text": c.chunk_text,
                "document_name": c.document_name,
                "document_id": str(c.document_id),
                "chunk_index": c.chunk_index,
                "relevance_score": float(c.relevance_score),
                "section": " > ".join(section_parts),
            })

        return {
            "answer": answer,
            "citations": citations,
            "search_mode": search_mode,
            "chunks_retrieved": len(chunks),
        }
