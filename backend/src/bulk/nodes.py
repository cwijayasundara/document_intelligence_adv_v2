"""Individual node functions for the bulk processing pipeline.

Each node takes a DocumentState dict and returns updates to merge.
In production, these would wrap real service calls with error handling.
"""

from __future__ import annotations

import time
from typing import Any

from src.bulk.state import DocumentState


async def parse_node(state: DocumentState) -> dict[str, Any]:
    """Parse the document content. Stub: sets parsed_content."""
    start = time.time()
    parsed = state.get("parsed_content", "")
    if not parsed:
        parsed = f"Parsed content for document {state.get('document_id', '')}"
    return {
        "parsed_content": parsed,
        "status": "parsed",
        "node_timings": {
            **state.get("node_timings", {}),
            "parse": time.time() - start,
        },
    }


async def classify_node(state: DocumentState) -> dict[str, Any]:
    """Classify the document. Stub: returns default classification."""
    start = time.time()
    return {
        "classification_result": {
            "category_name": "Other/Unclassified",
            "reasoning": "Bulk classification stub",
        },
        "status": "classified",
        "node_timings": {
            **state.get("node_timings", {}),
            "classify": time.time() - start,
        },
    }


async def extract_node(state: DocumentState) -> dict[str, Any]:
    """Extract fields from the document. Stub: returns empty list."""
    start = time.time()
    return {
        "extraction_results": [],
        "status": "extracted",
        "node_timings": {
            **state.get("node_timings", {}),
            "extract": time.time() - start,
        },
    }


async def judge_node(state: DocumentState) -> dict[str, Any]:
    """Judge extraction confidence. Stub: returns empty evaluations."""
    start = time.time()
    return {
        "judge_results": [],
        "status": "judged",
        "node_timings": {
            **state.get("node_timings", {}),
            "judge": time.time() - start,
        },
    }


async def summarize_node(state: DocumentState) -> dict[str, Any]:
    """Summarize the document. Stub: generates placeholder summary."""
    start = time.time()
    doc_id = state.get("document_id", "unknown")
    return {
        "summary": f"Summary for document {doc_id}",
        "status": "summarized",
        "node_timings": {
            **state.get("node_timings", {}),
            "summarize": time.time() - start,
        },
    }


async def ingest_node(state: DocumentState) -> dict[str, Any]:
    """Ingest document into vector store. Stub: marks ingested."""
    start = time.time()
    return {
        "status": "ingested",
        "node_timings": {
            **state.get("node_timings", {}),
            "ingest": time.time() - start,
        },
    }


async def finalize_node(state: DocumentState) -> dict[str, Any]:
    """Finalize the pipeline: set end time and status."""
    end_time = time.time()
    error = state.get("error")
    final_status = "failed" if error else "completed"
    return {
        "status": final_status,
        "end_time_ms": end_time,
        "node_timings": {
            **state.get("node_timings", {}),
            "finalize": 0.0,
        },
    }
