"""Unified LangGraph pipeline for document processing.

Handles both single-document and bulk flows with confidence-based
routing gates. Low-confidence documents pause for human review;
high-confidence documents flow through automatically.

Graph structure:
    parse → [route_after_parse] → summarize → classify → extract
                │                                           │
                └→ await_parse_review → summarize    [route_after_extract]
                                                            │
                                                     ┌──────┴──────┐
                                                  ingest    await_extraction_review
                                                     │             │
                                                  finalize      ingest → finalize
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph

from src.bulk.gates import route_after_extract, route_after_parse
from src.bulk.nodes import (
    classify_node,
    extract_node,
    finalize_node,
    ingest_node,
    parse_node,
    summarize_node,
)
from src.bulk.state import DocumentState
from src.bulk.wait_nodes import (
    await_extraction_review_node,
    await_parse_review_node,
)

logger = logging.getLogger(__name__)

DEFAULT_CONCURRENCY = 10


def build_pipeline(checkpointer: Any | None = None) -> Any:
    """Build and compile the unified processing StateGraph."""
    graph = StateGraph(DocumentState)

    # Processing nodes
    graph.add_node("parse", parse_node)
    graph.add_node("await_parse_review", await_parse_review_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("classify", classify_node)
    graph.add_node("extract", extract_node)
    graph.add_node("await_extraction_review", await_extraction_review_node)
    graph.add_node("ingest", ingest_node)
    graph.add_node("finalize", finalize_node)

    # Entry point
    graph.set_entry_point("parse")

    # Conditional edge after parse: check confidence
    graph.add_conditional_edges(
        "parse",
        route_after_parse,
        {"summarize": "summarize", "await_parse_review": "await_parse_review"},
    )
    graph.add_edge("await_parse_review", "summarize")

    # Linear edges through classify and extract
    graph.add_edge("summarize", "classify")
    graph.add_edge("classify", "extract")

    # Conditional edge after extract: check review flags
    graph.add_conditional_edges(
        "extract",
        route_after_extract,
        {"ingest": "ingest", "await_extraction_review": "await_extraction_review"},
    )
    graph.add_edge("await_extraction_review", "ingest")

    # Final edges
    graph.add_edge("ingest", "finalize")
    graph.set_finish_point("finalize")

    saver = checkpointer or MemorySaver()
    return graph.compile(
        checkpointer=saver,
        interrupt_before=["await_parse_review", "await_extraction_review"],
    )


async def create_checkpointer(engine: AsyncEngine) -> Any:
    """Build an asyncpg-backed LangGraph checkpointer from a shared engine.

    Thin adapter around ``langgraph_checkpoint_asyncpg.create_checkpointer``
    so callers don't need to import the third-party package directly.
    """
    from langgraph_checkpoint_asyncpg import create_checkpointer as _make

    return await _make(engine, auto_setup=True)


async def run_pipeline_for_document(
    compiled_graph: Any,
    initial_state: DocumentState,
) -> DocumentState:
    """Run the pipeline for a single document.

    Args:
        compiled_graph: Compiled StateGraph.
        initial_state: Pre-populated state with document info.

    Returns:
        Final DocumentState after pipeline execution (or interrupt).
    """
    doc_id = initial_state.get("document_id", "unknown")
    logger.info(
        "[pipeline:%s] Starting for %s",
        doc_id[:8],
        initial_state.get("file_name"),
    )

    result = await compiled_graph.ainvoke(
        initial_state,
        config={"configurable": {"thread_id": doc_id}},
    )
    return result


async def run_bulk_pipeline(
    document_states: list[DocumentState],
    concurrent_limit: int = DEFAULT_CONCURRENCY,
) -> list[DocumentState]:
    """Run the pipeline for multiple documents concurrently.

    Args:
        document_states: List of pre-populated DocumentState dicts.
        concurrent_limit: Max concurrent documents (default 10).

    Returns:
        List of final DocumentState results.
    """
    checkpointer = MemorySaver()

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
    paused = sum(1 for s in final if s.get("status", "").startswith("awaiting_"))
    logger.info(
        "Bulk pipeline finished: %d completed, %d failed, %d awaiting review",
        completed,
        failed,
        paused,
    )
    return final
