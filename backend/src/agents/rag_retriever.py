"""RAG retriever subagent for document search via Weaviate."""

from __future__ import annotations

import logging

from deepagents import SubAgent, create_deep_agent

from src.rag.reranker import rerank
from src.rag.weaviate_client import SearchResult, WeaviateClient

# Fetch this many chunks from Weaviate before re-ranking
_FETCH_K = 5
# Return this many chunks after re-ranking
_RERANK_TOP_N = 2

logger = logging.getLogger(__name__)


class RAGRetrieverSubagent:
    """Subagent that retrieves relevant chunks and generates answers."""

    def __init__(self, weaviate_client: WeaviateClient) -> None:
        self._weaviate = weaviate_client
        self._agent = create_deep_agent(
            model="openai:gpt-5.4-mini",
            tools=[],
            system_prompt=(
                "You are a RAG assistant for a Private Equity document intelligence system. "
                "Given a question and relevant document excerpts, generate a concise, "
                "accurate answer. Reference specific sections and quote key passages. "
                "If the excerpts don't contain enough information to answer, say so."
            ),
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        document_id: str | None = None,
        category_filter: str | None = None,
        alpha: float = 0.5,
    ) -> list[SearchResult]:
        """Retrieve and re-rank document chunks via hybrid search.

        Over-fetches from Weaviate, then re-ranks with a local
        cross-encoder model to improve relevance ordering.

        Args:
            query: Search query text.
            top_k: Number of final results to return.
            document_id: Optional single document filter.
            category_filter: Optional category name filter.
            alpha: Hybrid search balance (0=keyword, 1=semantic).

        Returns:
            List of SearchResult objects re-ranked by relevance.
        """
        logger.info(
            "Retrieving %d chunks from Weaviate (query='%s', alpha=%.1f, doc=%s)",
            _FETCH_K,
            query[:50],
            alpha,
            document_id or "all",
        )

        results = self._weaviate.search(
            query=query,
            top_k=_FETCH_K,
            alpha=alpha,
            document_id=document_id,
            category=category_filter,
        )
        logger.info("Weaviate returned %d chunks, re-ranking to top %d", len(results), _RERANK_TOP_N)

        reranked = rerank(query, results, top_n=_RERANK_TOP_N)
        return reranked

    async def generate_answer(
        self,
        query: str,
        chunks: list[SearchResult],
        conversation_history: str = "",
    ) -> str:
        """Generate an answer from retrieved chunks via LLM.

        Args:
            query: Original query.
            chunks: Retrieved search results with metadata.
            conversation_history: Previous Q&A exchanges for context.

        Returns:
            Generated answer string.
        """
        context_parts = []
        for c in chunks:
            header = f"[{c.document_name} — Chunk {c.chunk_index}]"
            meta_parts = []
            if c.metadata.get("header_1"):
                meta_parts.append(c.metadata["header_1"])
            if c.metadata.get("header_2"):
                meta_parts.append(c.metadata["header_2"])
            if c.metadata.get("header_3"):
                meta_parts.append(c.metadata["header_3"])
            section = f" ({' > '.join(meta_parts)})" if meta_parts else ""
            context_parts.append(f"{header}{section}\n{c.chunk_text}")

        context = "\n\n---\n\n".join(context_parts)

        history_block = ""
        if conversation_history:
            history_block = (
                f"## Previous conversation\n{conversation_history}\n\n"
            )

        prompt = (
            f"{history_block}"
            f"Based on the following document excerpts, answer the question.\n\n"
            f"Question: {query}\n\n"
            f"Document excerpts:\n{context}\n\n"
            f"Provide a clear answer, citing specific sections where relevant. "
            f"If this is a follow-up question, use the conversation context."
        )
        result = await self._agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]}
        )

        messages = result.get("messages", [])
        if messages:
            last = messages[-1]
            content = getattr(last, "content", None)
            if content is not None:
                # Handle list-of-blocks format: [{"type": "text", "text": "..."}]
                if isinstance(content, list):
                    parts = []
                    for block in content:
                        if isinstance(block, dict) and "text" in block:
                            parts.append(block["text"])
                        elif isinstance(block, str):
                            parts.append(block)
                    return "\n".join(parts)
                if isinstance(content, str):
                    return content
        return result.get("response", "Unable to generate answer.")

    def as_subagent_config(self) -> SubAgent:
        """Create a subagent config dict for orchestrator registration."""
        return SubAgent(
            name="rag_retriever",
            description="Retrieves relevant document chunks via hybrid search",
            system_prompt="You are a RAG retriever.",
            tools=[],
            model="openai:gpt-5.4-mini",
        )
