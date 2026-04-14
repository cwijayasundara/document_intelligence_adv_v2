"""RAG service orchestrating retrieval and answer generation."""

from __future__ import annotations

import logging
from typing import Any

from src.graph_nodes.rag_retriever import generate_answer, retrieve_chunks
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

    async def query(
        self,
        query: str,
        scope: str,
        scope_id: str | None = None,
        search_mode: str = "hybrid",
        top_k: int = 5,
        session_id: str | None = None,
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

        chunks = retrieve_chunks(
            weaviate_client=self._weaviate,
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

        # Load conversation history for multi-turn context
        conversation_history = ""
        if session_id:
            from src.graph_nodes.memory import get_short_term_memory

            memory = get_short_term_memory()
            conversation_history = memory.get_conversation_summary(session_id)

        logger.info(
            "Generating answer from %d chunks via LLM (session=%s, history=%d chars)",
            len(chunks),
            session_id or "none",
            len(conversation_history),
        )
        # Use agentic RAG for richer answers (query reformulation, multi-tool)
        try:
            from src.rag.agent import agentic_rag_query

            answer = await agentic_rag_query(
                query=query,
                weaviate_client=self._weaviate,
                document_id=doc_id,
                category_filter=category,
                conversation_history=conversation_history,
            )
        except Exception as exc:
            logger.warning("Agentic RAG failed, falling back to basic: %s", exc)
            answer = await generate_answer(query, chunks, conversation_history=conversation_history)

        # Save to short-term memory
        if session_id:
            memory = get_short_term_memory()
            memory.add_human_message(session_id, query)
            memory.add_ai_message(session_id, answer)

        # Save query pattern to long-term memory (fire-and-forget)
        try:
            from src.graph_nodes.memory.store import save_correction

            await save_correction(
                user_id="system",
                correction_type="rag_query_patterns",
                key=f"q_{hash(query) % 100000}",
                data={"query": query, "scope": scope, "chunks": len(chunks)},
            )
        except Exception:
            pass  # Non-critical — don't fail the request

        from src.rag.formatting import build_citation

        citations = [build_citation(c) for c in chunks]

        return {
            "answer": answer,
            "citations": citations,
            "search_mode": search_mode,
            "chunks_retrieved": len(chunks),
        }
