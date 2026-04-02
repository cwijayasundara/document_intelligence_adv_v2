"""Individual node functions for the bulk processing pipeline.

Each node takes a DocumentState dict and returns updates to merge.
Nodes wrap real service calls with error handling and timing.
"""

from __future__ import annotations

import time
from typing import Any

from src.agents.classifier import ClassifierSubagent
from src.agents.extractor import ExtractorSubagent
from src.agents.judge import JudgeSubagent
from src.agents.summarizer import SummarizerSubagent
from src.bulk.state import DocumentState


async def parse_node(state: DocumentState) -> dict[str, Any]:
    """Parse the document content.

    If parsed_content is already provided, uses it directly.
    Otherwise generates a placeholder (real parsing requires DB + Reducto).
    """
    start = time.time()
    try:
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
    except Exception as exc:
        return {
            "status": "failed",
            "error": str(exc),
            "node_timings": {
                **state.get("node_timings", {}),
                "parse": time.time() - start,
            },
        }


async def classify_node(state: DocumentState) -> dict[str, Any]:
    """Classify the document using the ClassifierSubagent."""
    start = time.time()
    try:
        classifier = ClassifierSubagent()
        parsed_content = state.get("parsed_content", "")
        file_name = state.get("file_name", "unknown")
        summary_text = state.get("summary_text")

        # Default categories for bulk pipeline; in production these come from DB
        categories: list[dict[str, Any]] = state.get("categories", [])  # type: ignore[assignment]

        result = await classifier.classify(
            file_name=file_name,
            content=parsed_content,
            categories=categories,
            summary=summary_text,
        )
        return {
            "classification_result": {
                "category_id": str(result.category_id),
                "category_name": result.category_name,
                "confidence": result.confidence,
                "reasoning": result.reasoning,
            },
            "status": "classified",
            "node_timings": {
                **state.get("node_timings", {}),
                "classify": time.time() - start,
            },
        }
    except Exception as exc:
        return {
            "classification_result": {
                "category_name": "Other/Unclassified",
                "reasoning": f"Classification failed: {exc}",
            },
            "status": "classified",
            "error": str(exc),
            "node_timings": {
                **state.get("node_timings", {}),
                "classify": time.time() - start,
            },
        }


async def extract_node(state: DocumentState) -> dict[str, Any]:
    """Extract fields from the document using the ExtractorSubagent."""
    start = time.time()
    try:
        extractor = ExtractorSubagent()
        parsed_content = state.get("parsed_content", "")

        # Extraction fields come from the category schema; default to empty
        extraction_fields: list[dict[str, Any]] = state.get("extraction_fields", [])  # type: ignore[assignment]

        result = await extractor.extract(parsed_content, extraction_fields)
        return {
            "extraction_results": [f.model_dump() for f in result.fields],
            "status": "extracted",
            "node_timings": {
                **state.get("node_timings", {}),
                "extract": time.time() - start,
            },
        }
    except Exception as exc:
        return {
            "extraction_results": [],
            "status": "extracted",
            "error": str(exc),
            "node_timings": {
                **state.get("node_timings", {}),
                "extract": time.time() - start,
            },
        }


async def judge_node(state: DocumentState) -> dict[str, Any]:
    """Judge extraction confidence using the JudgeSubagent."""
    start = time.time()
    try:
        from src.agents.schemas.extraction import ExtractedField

        judge = JudgeSubagent()
        parsed_content = state.get("parsed_content", "")
        extraction_results = state.get("extraction_results", [])

        extracted_fields = [ExtractedField(**er) for er in extraction_results]

        result = await judge.evaluate(extracted_fields, parsed_content)
        return {
            "judge_results": [e.model_dump() for e in result.evaluations],
            "status": "judged",
            "node_timings": {
                **state.get("node_timings", {}),
                "judge": time.time() - start,
            },
        }
    except Exception as exc:
        return {
            "judge_results": [],
            "status": "judged",
            "error": str(exc),
            "node_timings": {
                **state.get("node_timings", {}),
                "judge": time.time() - start,
            },
        }


async def summarize_node(state: DocumentState) -> dict[str, Any]:
    """Summarize the document using the SummarizerSubagent."""
    start = time.time()
    try:
        summarizer = SummarizerSubagent()
        parsed_content = state.get("parsed_content", "")

        result = await summarizer.summarize(parsed_content)
        return {
            "summary": result.summary,
            "status": "summarized",
            "node_timings": {
                **state.get("node_timings", {}),
                "summarize": time.time() - start,
            },
        }
    except Exception as exc:
        doc_id = state.get("document_id", "unknown")
        return {
            "summary": f"Summary generation failed for document {doc_id}",
            "status": "summarized",
            "error": str(exc),
            "node_timings": {
                **state.get("node_timings", {}),
                "summarize": time.time() - start,
            },
        }


async def ingest_node(state: DocumentState) -> dict[str, Any]:
    """Ingest document into vector store.

    In the bulk pipeline context, full ingestion requires a WeaviateClient
    and chunker. This node marks the status; real ingestion is done
    by the IngestionService when infrastructure is available.
    """
    start = time.time()
    try:
        return {
            "status": "ingested",
            "node_timings": {
                **state.get("node_timings", {}),
                "ingest": time.time() - start,
            },
        }
    except Exception as exc:
        return {
            "status": "ingested",
            "error": str(exc),
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
