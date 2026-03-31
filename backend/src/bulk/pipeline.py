"""LangGraph-based bulk processing pipeline.

Builds a StateGraph with 7 nodes: parse, classify, extract, judge,
summarize, ingest, finalize. Supports concurrent document processing
with asyncio.Semaphore and MemorySaver checkpointing.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph

# AsyncPostgresSaver is imported lazily to avoid hard dependency on psycopg at import time.
# Use create_checkpointer() to instantiate it at runtime.
from src.bulk.nodes import (
    classify_node,
    extract_node,
    finalize_node,
    ingest_node,
    judge_node,
    parse_node,
    summarize_node,
)
from src.bulk.state import DocumentState

DEFAULT_CONCURRENCY = 10


async def create_checkpointer(conn_string: str) -> Any:
    """Create a persistent AsyncPostgresSaver checkpointer.

    Args:
        conn_string: Sync PostgreSQL connection string (postgresql://...).

    Returns:
        Configured AsyncPostgresSaver instance.
    """
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    saver = AsyncPostgresSaver.from_conn_string(conn_string)
    await saver.setup()
    return saver


def build_pipeline(
    checkpointer: Any | None = None,
) -> Any:
    """Build and compile the bulk processing StateGraph.

    Args:
        checkpointer: Optional checkpointer for resumability (MemorySaver or AsyncPostgresSaver).

    Returns:
        Compiled graph ready for invocation.
    """
    graph = StateGraph(DocumentState)

    graph.add_node("parse_node", parse_node)
    graph.add_node("classify_node", classify_node)
    graph.add_node("extract_node", extract_node)
    graph.add_node("judge_node", judge_node)
    graph.add_node("summarize_node", summarize_node)
    graph.add_node("ingest_node", ingest_node)
    graph.add_node("finalize_node", finalize_node)

    graph.add_edge("parse_node", "classify_node")
    graph.add_edge("classify_node", "extract_node")
    graph.add_edge("extract_node", "judge_node")
    graph.add_edge("judge_node", "summarize_node")
    graph.add_edge("summarize_node", "ingest_node")
    graph.add_edge("ingest_node", "finalize_node")

    graph.set_entry_point("parse_node")
    graph.set_finish_point("finalize_node")

    saver = checkpointer or MemorySaver()
    return graph.compile(checkpointer=saver)


async def run_pipeline_for_document(
    compiled_graph: Any,
    document_id: str,
    initial_content: str = "",
) -> DocumentState:
    """Run the pipeline for a single document.

    Args:
        compiled_graph: Compiled StateGraph.
        document_id: UUID string of the document.
        initial_content: Optional initial parsed content.

    Returns:
        Final DocumentState after pipeline execution.
    """
    initial_state: DocumentState = {
        "document_id": document_id,
        "status": "pending",
        "parsed_content": initial_content,
        "classification_result": {},
        "extraction_results": [],
        "judge_results": [],
        "summary": "",
        "error": None,
        "start_time_ms": time.time(),
        "end_time_ms": 0.0,
        "node_timings": {},
    }

    result = await compiled_graph.ainvoke(
        initial_state,
        config={"configurable": {"thread_id": document_id}},
    )
    return result


async def run_bulk_pipeline(
    document_ids: list[str],
    concurrent_limit: int = DEFAULT_CONCURRENCY,
    checkpointer: Any | None = None,
    db_url: str | None = None,
) -> list[DocumentState]:
    """Run the bulk pipeline for multiple documents concurrently.

    Args:
        document_ids: List of document UUID strings.
        concurrent_limit: Max concurrent documents.
        checkpointer: Optional checkpointer instance (MemorySaver or AsyncPostgresSaver).
        db_url: Optional sync PostgreSQL URL; creates AsyncPostgresSaver if provided.

    Returns:
        List of final DocumentState results.
    """
    if checkpointer is None and db_url is not None:
        checkpointer = await create_checkpointer(db_url)
    compiled = build_pipeline(checkpointer=checkpointer)
    semaphore = asyncio.Semaphore(concurrent_limit)

    async def _process(doc_id: str) -> DocumentState:
        async with semaphore:
            return await run_pipeline_for_document(compiled, doc_id)

    tasks = [_process(doc_id) for doc_id in document_ids]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    return list(results)
