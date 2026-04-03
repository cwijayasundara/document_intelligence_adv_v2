"""Pipeline nodes for bulk document processing.

Each node reuses the same service classes as single-doc endpoints.
Nodes take a DocumentState dict and return updates to merge.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from src.bulk.state import DocumentState

logger = logging.getLogger(__name__)


def _timing(state: DocumentState, name: str, start: float) -> dict[str, float]:
    return {**state.get("node_timings", {}), name: time.time() - start}


def _lookup_extraction_fields(
    state: DocumentState, category_id: str,
) -> list[dict[str, Any]]:
    """Look up extraction fields for a category from the state's fields map."""
    fields_map: dict[str, list[dict[str, Any]]] = state.get(
        "extraction_fields_map", {}
    )  # type: ignore[assignment]
    fields = fields_map.get(category_id, [])
    logger.info("[bulk] Found %d extraction fields for category %s", len(fields), category_id[:8])
    return fields


async def parse_node(state: DocumentState) -> dict[str, Any]:
    """Parse document via Reducto using ParseService (same as single-doc)."""
    start = time.time()
    doc_id = state.get("document_id", "")

    try:
        from src.config.settings import get_settings
        from src.db.connection import get_session_factory
        from src.db.repositories.documents import DocumentRepository
        from src.parser.reducto import ReductoClient
        from src.services.parse_service import ParseService
        from src.storage.local import LocalStorage

        settings = get_settings()
        factory = get_session_factory()
        async with factory() as session:
            repo = DocumentRepository(session)
            storage = LocalStorage(
                upload_dir=settings.storage.upload_dir,
                parsed_dir=settings.storage.parsed_dir,
            )
            reducto = ReductoClient(
                api_key=settings.reducto_api_key,
                base_url=settings.reducto_base_url,
            )
            service = ParseService(repo=repo, storage=storage, reducto_client=reducto)

            logger.info("[bulk:%s] Parsing via Reducto", doc_id[:8])
            doc, content, was_skipped, confidence = await service.parse_document(
                uuid.UUID(doc_id), force=False,
            )
            await session.commit()

            logger.info(
                "[bulk:%s] Parsed %d chars (skipped=%s, confidence=%.1f%%)",
                doc_id[:8], len(content), was_skipped, confidence,
            )
            return {
                "parsed_content": content,
                "parsed_path": doc.parsed_path or "",
                "status": "parsed",
                "node_timings": _timing(state, "parse", start),
            }
    except Exception as exc:
        logger.error("[bulk:%s] Parse failed: %s", doc_id[:8], exc)
        return {"status": "failed", "error": str(exc),
                "node_timings": _timing(state, "parse", start)}


async def summarize_node(state: DocumentState) -> dict[str, Any]:
    """Summarize document using SummaryService (same as single-doc)."""
    start = time.time()
    doc_id = state.get("document_id", "")

    try:
        from src.config.settings import get_settings
        from src.services.summarize_service import SummaryService

        settings = get_settings()
        parsed_content = state.get("parsed_content", "")
        service = SummaryService(summary_dir=settings.storage.summary_dir)
        result = await service.generate_summary(uuid.UUID(doc_id), parsed_content)

        summary = result.get("summary", "")
        logger.info("[bulk:%s] Summary generated (%d chars)", doc_id[:8], len(summary))
        return {
            "summary_text": summary,
            "status": "summarized",
            "node_timings": _timing(state, "summarize", start),
        }
    except Exception as exc:
        logger.error("[bulk:%s] Summarize failed: %s", doc_id[:8], exc)
        return {"summary_text": "", "status": "summarized", "error": str(exc),
                "node_timings": _timing(state, "summarize", start)}


async def classify_node(state: DocumentState) -> dict[str, Any]:
    """Classify document using ClassifierSubagent (same as single-doc)."""
    start = time.time()
    doc_id = state.get("document_id", "")

    try:
        from src.agents.classifier import ClassifierSubagent

        classifier = ClassifierSubagent()
        result = await classifier.classify(
            file_name=state.get("file_name", "unknown"),
            content=state.get("parsed_content", ""),
            categories=state.get("categories", []),  # type: ignore[arg-type]
            summary=state.get("summary_text"),
        )

        cat_id = str(result.category_id)
        extraction_fields = _lookup_extraction_fields(state, cat_id)

        logger.info(
            "[bulk:%s] Classified as '%s' (confidence=%d%%)",
            doc_id[:8], result.category_name, result.confidence,
        )
        return {
            "classification_result": {
                "category_id": cat_id,
                "category_name": result.category_name,
                "confidence": result.confidence,
                "reasoning": result.reasoning,
            },
            "category_id": cat_id,
            "category_name": result.category_name,
            "extraction_fields": extraction_fields,
            "status": "classified",
            "node_timings": _timing(state, "classify", start),
        }
    except Exception as exc:
        logger.error("[bulk:%s] Classify failed: %s", doc_id[:8], exc)
        return {
            "classification_result": {"category_name": "Other/Unclassified", "reasoning": str(exc)},
            "status": "classified", "error": str(exc),
            "node_timings": _timing(state, "classify", start),
        }


async def extract_node(state: DocumentState) -> dict[str, Any]:
    """Extract fields using ExtractionService (same as single-doc)."""
    start = time.time()
    doc_id = state.get("document_id", "")

    try:
        from src.config.settings import get_settings
        from src.services.extraction_service import ExtractionService

        settings = get_settings()
        extraction_fields: list[dict[str, Any]] = state.get(
            "extraction_fields", []
        )  # type: ignore[assignment]

        if not extraction_fields:
            logger.info("[bulk:%s] No extraction fields, skipping", doc_id[:8])
            return {"extraction_results": [], "status": "extracted",
                    "node_timings": _timing(state, "extract", start)}

        service = ExtractionService(extraction_dir=settings.storage.extraction_dir)
        results = await service.extract_and_judge(
            doc_id=uuid.UUID(doc_id),
            parsed_content=state.get("parsed_content", ""),
            extraction_fields=extraction_fields,
        )
        logger.info("[bulk:%s] Extracted %d fields", doc_id[:8], len(results))
        return {
            "extraction_results": results,
            "status": "extracted",
            "node_timings": _timing(state, "extract", start),
        }
    except Exception as exc:
        logger.error("[bulk:%s] Extract failed: %s", doc_id[:8], exc)
        return {"extraction_results": [], "status": "extracted", "error": str(exc),
                "node_timings": _timing(state, "extract", start)}


async def ingest_node(state: DocumentState) -> dict[str, Any]:
    """Ingest to Weaviate using IngestionService (same as single-doc)."""
    start = time.time()
    doc_id = state.get("document_id", "")

    try:
        from src.config.settings import get_settings
        from src.rag.chunker import DocumentChunker
        from src.rag.weaviate_client import WeaviateClient
        from src.services.ingest_service import IngestionService

        settings = get_settings()
        weaviate = WeaviateClient(url=settings.weaviate_url)
        weaviate.connect()

        chunker = DocumentChunker(
            max_tokens=settings.chunking.max_tokens,
            overlap_tokens=settings.chunking.overlap_tokens,
        )
        service = IngestionService(weaviate_client=weaviate, chunker=chunker)

        chunks_created = service.ingest_document(
            document_id=uuid.UUID(doc_id),
            document_name=state.get("file_name", ""),
            document_category=state.get("category_name", ""),
            file_name=state.get("file_name", ""),
            parsed_content=state.get("parsed_content", ""),
        )
        weaviate.disconnect()

        logger.info("[bulk:%s] Ingested %d chunks", doc_id[:8], chunks_created)
        return {
            "chunks_created": chunks_created,
            "status": "ingested",
            "node_timings": _timing(state, "ingest", start),
        }
    except Exception as exc:
        logger.error("[bulk:%s] Ingest failed: %s", doc_id[:8], exc)
        return {"status": "ingested", "error": str(exc),
                "node_timings": _timing(state, "ingest", start)}


async def finalize_node(state: DocumentState) -> dict[str, Any]:
    """Set final status and end time."""
    error = state.get("error")
    final_status = "failed" if error else "completed"
    logger.info(
        "[bulk:%s] Finalized: %s (timings: %s)",
        state.get("document_id", "")[:8], final_status, state.get("node_timings", {}),
    )
    return {
        "status": final_status,
        "end_time_ms": time.time(),
        "node_timings": {**state.get("node_timings", {}), "finalize": 0.0},
    }
