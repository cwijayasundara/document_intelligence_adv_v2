"""RAG retriever functions for document search via Weaviate."""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.llm import get_llm
from src.agents.middleware.decorators import with_retry, with_telemetry
from src.agents.middleware.pii_filter import PIIFilterMiddleware
from src.rag.reranker import rerank
from src.rag.weaviate_client import SearchResult, WeaviateClient

# Fetch this many chunks from Weaviate before re-ranking
_FETCH_K = 5
# Return this many chunks after re-ranking
_RERANK_TOP_N = 2

logger = logging.getLogger(__name__)

_pii_filter = PIIFilterMiddleware()

_SYSTEM_PROMPT = (
    "You are a RAG assistant for a Private Equity document intelligence system. "
    "Given a question and relevant document excerpts, generate a concise, "
    "accurate answer. Reference specific sections and quote key passages. "
    "If the excerpts don't contain enough information to answer, say so."
)


def retrieve_chunks(
    weaviate_client: WeaviateClient,
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
        weaviate_client: Weaviate client instance.
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

    results = weaviate_client.search(
        query=query,
        top_k=_FETCH_K,
        alpha=alpha,
        document_id=document_id,
        category=category_filter,
    )
    logger.info("Weaviate returned %d chunks, re-ranking to top %d", len(results), _RERANK_TOP_N)

    reranked = rerank(query, results, top_n=_RERANK_TOP_N)
    return reranked


@with_retry(max_retries=3)
@with_telemetry(node_name="rag_answer")
async def generate_answer(
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
    from src.rag.formatting import format_chunks_as_context

    context = format_chunks_as_context(chunks)
    # Filter PII from context before sending to LLM
    filtered = _pii_filter.filter_content(context)
    context = filtered.redacted_text

    history_block = ""
    if conversation_history:
        history_block = f"## Previous conversation\n{conversation_history}\n\n"

    prompt = (
        f"{history_block}"
        f"Based on the following document excerpts, answer the question.\n\n"
        f"Question: {query}\n\n"
        f"Document excerpts:\n{context}\n\n"
        f"Provide a clear answer, citing specific sections where relevant. "
        f"If this is a follow-up question, use the conversation context."
    )

    llm = get_llm()
    response = await llm.ainvoke(
        [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
    )
    answer = response.content
    # Handle content that may be a string or list of content blocks
    if isinstance(answer, list):
        answer = " ".join(
            block.get("text", "") if isinstance(block, dict) else str(block) for block in answer
        )
    return answer or "Unable to generate answer."
