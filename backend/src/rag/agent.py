"""Agentic RAG using LangChain's create_agent.

The agent decides whether to search, can reformulate queries,
look up extraction results, and grade retrieved chunks before
generating an answer. Falls back to direct answer when retrieval
is not needed (e.g. conversational follow-ups).

Tools available to the agent:
- search_documents: Hybrid search in Weaviate with reranking
- lookup_extractions: Query previously extracted field values
- get_document_summary: Retrieve a cached document summary
"""

from __future__ import annotations

import logging
import uuid

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from src.graph_nodes.llm import get_llm
from src.graph_nodes.middleware.pii_filter import PIIFilterMiddleware
from src.rag.weaviate_client import WeaviateClient

logger = logging.getLogger(__name__)

_pii_filter = PIIFilterMiddleware()

_SYSTEM_PROMPT = """\
You are a RAG assistant for a Private Equity document intelligence platform.

You have access to tools for searching PE documents (LPAs, subscription \
agreements, side letters) and looking up extracted field values.

## How to answer questions

1. **Decide if retrieval is needed.** For conversational follow-ups, \
greetings, or questions about previous answers, respond directly.

2. **Search documents** using the search_documents tool. You can:
   - Search all documents or filter by a specific document/category
   - Reformulate vague queries into precise search terms
   - Search multiple times with different queries if initial results \
are insufficient

3. **Look up extracted values** using lookup_extractions when the user \
asks about specific fields (e.g. "what's the management fee?").

4. **Get document summaries** using get_document_summary for overview \
questions about a specific document.

5. **Generate your answer** from the retrieved information:
   - Reference specific sections and quote key passages
   - If the information is insufficient, say so honestly
   - For PE-specific terms, use precise financial/legal language

## Important
- Always cite which document and section your answer comes from
- If results seem irrelevant, try reformulating your search query
- Prefer extraction results over raw text for structured fields \
(fees, dates, percentages)
"""


def _create_tools(
    weaviate_client: WeaviateClient,
    document_id: str | None = None,
    category_filter: str | None = None,
) -> list:
    """Create tools for the RAG agent scoped to the query context."""
    from src.graph_nodes.rag_retriever import retrieve_chunks

    @tool
    async def search_documents(query: str) -> str:
        """Search PE documents in the knowledge base.

        Use for questions about fund terms, legal provisions,
        partnership agreements, fees, returns, etc.
        Returns relevant document excerpts with source information.
        """
        import asyncio

        chunks = await asyncio.to_thread(
            retrieve_chunks,
            weaviate_client=weaviate_client,
            query=query,
            document_id=document_id,
            category_filter=category_filter,
        )
        if not chunks:
            return "No relevant documents found for this query."

        from src.rag.formatting import format_chunks_as_context

        return format_chunks_as_context(chunks)

    @tool
    async def lookup_extractions(doc_id: str, field_name: str | None = None) -> str:
        """Look up previously extracted field values for a document.

        Use when the user asks about specific fields like management
        fee rate, carried interest, fund term, etc. Returns structured
        extraction results with confidence scores.

        Args:
            doc_id: The document UUID to look up.
            field_name: Optional specific field name to filter by.
        """
        try:
            from src.db.connection import get_session_factory
            from src.db.repositories.extracted_values import (
                ExtractedValuesRepository,
            )

            factory = get_session_factory()
            async with factory() as session:
                repo = ExtractedValuesRepository(session)
                values = await repo.get_by_document(uuid.UUID(doc_id))
                if not values:
                    return f"No extraction results found for document {doc_id}."

                lines = []
                for v in values:
                    if field_name and v.field.field_name != field_name:
                        continue
                    lines.append(
                        f"- {v.field.display_name}: {v.extracted_value or '(empty)'} "
                        f"[confidence: {v.confidence}]"
                    )
                return "\n".join(lines) if lines else "No matching fields found."
        except Exception as exc:
            return f"Error looking up extractions: {exc}"

    @tool
    async def get_document_summary(doc_id: str) -> str:
        """Get the summary of a specific document.

        Use for overview questions like "what is this document about?"
        or when you need a high-level understanding before searching
        for specific details.

        Args:
            doc_id: The document UUID.
        """
        try:
            from src.config.settings import get_settings
            from src.services.summarize_service import SummaryService

            settings = get_settings()
            service = SummaryService(summary_dir=settings.storage.summary_dir)
            cached = await service.get_cached_summary(uuid.UUID(doc_id))
            if cached:
                return cached.get("summary", "No summary available.")
            return f"No summary found for document {doc_id}."
        except Exception as exc:
            return f"Error loading summary: {exc}"

    tools = [search_documents, lookup_extractions, get_document_summary]
    return tools


async def agentic_rag_query(
    query: str,
    weaviate_client: WeaviateClient,
    document_id: str | None = None,
    category_filter: str | None = None,
    conversation_history: str = "",
) -> str:
    """Run an agentic RAG query using LangChain's react agent.

    The agent decides whether to search, can reformulate queries,
    and generates answers from retrieved context.

    Args:
        query: User's question.
        weaviate_client: Weaviate client for document search.
        document_id: Optional filter to a single document.
        category_filter: Optional filter by category.
        conversation_history: Previous conversation for context.

    Returns:
        Generated answer string.
    """
    from langchain.agents import create_agent

    # Filter PII from query
    filtered = _pii_filter.filter_content(query)
    query = filtered.redacted_text

    tools = _create_tools(
        weaviate_client=weaviate_client,
        document_id=document_id,
        category_filter=category_filter,
    )

    llm = get_llm()
    agent = create_agent(llm, tools)

    # Build message list
    messages = [SystemMessage(content=_SYSTEM_PROMPT)]
    if conversation_history:
        messages.append(SystemMessage(content=f"## Previous conversation\n{conversation_history}"))
    messages.append(HumanMessage(content=query))

    logger.info(
        "Running agentic RAG: query='%s', doc_id=%s, tools=%d",
        query[:80],
        document_id or "all",
        len(tools),
    )

    result = await agent.ainvoke({"messages": messages})

    # Extract the final answer from the last AI message
    final_messages = result.get("messages", [])
    if final_messages:
        last = final_messages[-1]
        content = getattr(last, "content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    parts.append(block["text"])
                elif isinstance(block, str):
                    parts.append(block)
            return "\n".join(parts)

    return "Unable to generate an answer."
