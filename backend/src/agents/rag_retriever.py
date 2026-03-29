"""RAG retriever subagent for document search via Weaviate."""

from __future__ import annotations

from typing import Any

from deepagents import SubAgent, create_deep_agent

from src.rag.weaviate_client import SearchResult, WeaviateClient


class RAGRetrieverSubagent:
    """Subagent that retrieves relevant chunks from Weaviate.

    Supports hybrid search with configurable alpha parameter
    for balancing keyword vs. semantic search.
    """

    def __init__(self, weaviate_client: WeaviateClient) -> None:
        self._weaviate = weaviate_client
        self._agent = create_deep_agent(
            model="openai:gpt-5.4-mini",
            tools=[self._search_documents],
            system_prompt=(
                "You are a RAG retriever for a PE document intelligence system. "
                "Given a question and relevant document excerpts, generate a concise "
                "answer with references to the source chunks."
            ),
        )

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        document_id: str | None = None,
        category_filter: str | None = None,
        alpha: float = 0.5,
    ) -> list[SearchResult]:
        """Retrieve relevant document chunks.

        Args:
            query: Search query text.
            top_k: Number of results to return.
            document_id: Optional single document filter.
            category_filter: Optional category name filter.
            alpha: Hybrid search balance (0=keyword, 1=semantic).

        Returns:
            List of SearchResult objects.
        """
        results = await self._weaviate.search(
            query=query,
            top_k=top_k,
            document_id=document_id,
        )

        if category_filter:
            results = [r for r in results if hasattr(r, "document_category")]

        return results

    async def generate_answer(
        self,
        query: str,
        chunks: list[SearchResult],
    ) -> str:
        """Generate an answer from retrieved chunks via LLM.

        Args:
            query: Original query.
            chunks: Retrieved search results.

        Returns:
            Generated answer string.
        """
        context = "\n\n".join(f"[Chunk {c.chunk_index}] {c.chunk_text}" for c in chunks)
        prompt = (
            f"Based on the following document excerpts, answer the question.\n\n"
            f"Question: {query}\n\nContext:\n{context}\n\n"
            f"Provide a concise answer with references to the source."
        )
        result = await self._agent.ainvoke(prompt)
        return result.get("response", "Unable to generate answer.")

    async def _search_documents(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Tool: search documents in Weaviate via hybrid search."""
        results = await self._weaviate.search(query=query, top_k=top_k)
        return [
            {
                "chunk_text": r.chunk_text,
                "document_id": r.document_id,
                "document_name": r.document_name,
                "chunk_index": r.chunk_index,
                "relevance_score": r.relevance_score,
            }
            for r in results
        ]

    def as_subagent_config(self) -> SubAgent:
        """Create a subagent config dict for orchestrator registration."""
        return SubAgent(
            name="rag_retriever",
            description="Retrieves relevant document chunks via hybrid search",
            system_prompt="You are a RAG retriever.",
            tools=[],
            model="openai:gpt-5.4-mini",
        )
