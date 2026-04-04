"""LangGraph-based bulk processing pipeline.

Node order: parse → summarize → classify → extract → ingest → finalize.
Supports concurrent processing of 10 documents via asyncio.Semaphore.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph

from src.bulk.nodes import (
    classify_node,
    extract_node,
    finalize_node,
    ingest_node,
    parse_node,
    summarize_node,
)
from src.bulk.state import DocumentState

logger = logging.getLogger(__name__)

DEFAULT_CONCURRENCY = 10


def build_pipeline(checkpointer: Any | None = None) -> Any:
    """Build and compile the bulk processing StateGraph."""
    graph = StateGraph(DocumentState)

    graph.add_node("parse", parse_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("classify", classify_node)
    graph.add_node("extract", extract_node)
    graph.add_node("ingest", ingest_node)
    graph.add_node("finalize", finalize_node)

    graph.add_edge("parse", "summarize")
    graph.add_edge("summarize", "classify")
    graph.add_edge("classify", "extract")
    graph.add_edge("extract", "ingest")
    graph.add_edge("ingest", "finalize")

    graph.set_entry_point("parse")
    graph.set_finish_point("finalize")

    saver = checkpointer or MemorySaver()
    return graph.compile(checkpointer=saver)


async def run_pipeline_for_document(
    compiled_graph: Any,
    initial_state: DocumentState,
) -> DocumentState:
    """Run the pipeline for a single document.

    Args:
        compiled_graph: Compiled StateGraph.
        initial_state: Pre-populated state with document info.

    Returns:
        Final DocumentState after pipeline execution.
    """
    doc_id = initial_state.get("document_id", "unknown")
    logger.info("[bulk:%s] Starting pipeline for %s", doc_id[:8], initial_state.get("file_name"))

    result = await compiled_graph.ainvoke(
        initial_state,
        config={"configurable": {"thread_id": doc_id}},
    )
    return result


async def run_bulk_pipeline(
    document_states: list[DocumentState],
    concurrent_limit: int = DEFAULT_CONCURRENCY,
) -> list[DocumentState]:
    """Run the bulk pipeline for multiple documents concurrently.

    Args:
        document_states: List of pre-populated DocumentState dicts.
        concurrent_limit: Max concurrent documents (default 10).

    Returns:
        List of final DocumentState results.
    """
    # Use persistent checkpointing if DB URL available
    checkpointer = None
    try:
        from src.config.settings import get_settings
        settings = get_settings()
        if settings.database_url:
            checkpointer = await create_checkpointer(settings.database_url_sync)
    except Exception:
        logger.warning("Could not create persistent checkpointer, using in-memory")

    compiled = build_pipeline(checkpointer=checkpointer)
    semaphore = asyncio.Semaphore(concurrent_limit)

    logger.info(
        "Starting bulk pipeline: %d documents, concurrency=%d",
        len(document_states),
        concurrent_limit,
    )

    async def _process(state: DocumentState) -> DocumentState:
        async with semaphore:
            return await run_pipeline_for_document(compiled, state)

    tasks = [_process(s) for s in document_states]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    final: list[DocumentState] = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            doc_id = document_states[i].get("document_id", "unknown")
            logger.error("[bulk:%s] Pipeline exception: %s", doc_id[:8], r)
            final.append(
                {
                    **document_states[i],
                    "status": "failed",
                    "error": str(r),
                    "end_time_ms": time.time(),
                }
            )
        else:
            final.append(r)

    completed = sum(1 for s in final if s.get("status") == "completed")
    failed = sum(1 for s in final if s.get("status") == "failed")
    logger.info("Bulk pipeline finished: %d completed, %d failed", completed, failed)
    return final
