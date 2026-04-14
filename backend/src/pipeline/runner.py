"""Unified pipeline runner for single and bulk document processing.

Provides start, resume, and retry_node operations backed by
LangGraph's checkpointer for state persistence and interrupt handling.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from src.bulk.pipeline import build_pipeline
from src.bulk.state import DocumentState

logger = logging.getLogger(__name__)

# Module-level compiled graph (lazy-initialized)
_compiled_graph: Any | None = None
_checkpointer: Any | None = None


def _get_checkpointer() -> Any:
    """Get or create a persistent checkpointer."""
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = MemorySaver()
    return _checkpointer


def _get_compiled_graph() -> Any:
    """Get or create the compiled pipeline graph."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_pipeline(checkpointer=_get_checkpointer())
    return _compiled_graph


class PipelineRunner:
    """Unified pipeline runner for document processing.

    Handles start, resume (after human review), and retry from
    a specific failed node. Works for both single and bulk documents.
    """

    def __init__(self, compiled_graph: Any | None = None) -> None:
        self._graph = compiled_graph or _get_compiled_graph()

    async def start(
        self,
        document_id: uuid.UUID,
        file_name: str,
        original_path: str,
        categories: list[dict[str, Any]],
        extraction_fields_map: dict[str, list[dict[str, Any]]],
    ) -> DocumentState:
        """Start the pipeline for a single document.

        Args:
            document_id: Document UUID.
            file_name: Original filename.
            original_path: Path to the uploaded file.
            categories: Available classification categories.
            extraction_fields_map: Category ID → extraction fields.

        Returns:
            Final or interrupted DocumentState.
        """
        doc_id = str(document_id)
        thread_id = doc_id

        initial_state: DocumentState = {
            "document_id": doc_id,
            "file_name": file_name,
            "original_path": original_path,
            "status": "processing",
            "categories": categories,
            "extraction_fields_map": extraction_fields_map,
            "start_time_ms": time.time(),
            "node_timings": {},
            "node_statuses": {},
            "pipeline_context": {},
        }

        # Persist thread_id on the document
        await self._save_thread_id(document_id, thread_id)

        logger.info("[runner:%s] Starting pipeline for %s", doc_id[:8], file_name)

        result = await self._graph.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": thread_id}},
        )

        logger.info(
            "[runner:%s] Pipeline result: status=%s",
            doc_id[:8],
            result.get("status", "unknown"),
        )
        return result

    async def resume(
        self,
        document_id: uuid.UUID,
        resume_data: dict[str, Any] | None = None,
    ) -> DocumentState:
        """Resume a paused pipeline after human review.

        Args:
            document_id: Document UUID.
            resume_data: Data to pass to the interrupt point.

        Returns:
            Final or next-interrupted DocumentState.
        """
        doc_id = str(document_id)
        thread_id = await self._get_thread_id(document_id) or doc_id

        logger.info("[runner:%s] Resuming pipeline", doc_id[:8])

        result = await self._graph.ainvoke(
            Command(resume=resume_data or {"approved": True}),
            config={"configurable": {"thread_id": thread_id}},
        )

        logger.info(
            "[runner:%s] Resume result: status=%s",
            doc_id[:8],
            result.get("status", "unknown"),
        )
        return result

    async def retry_node(
        self,
        document_id: uuid.UUID,
        node_name: str,
    ) -> DocumentState:
        """Retry a specific failed node by replaying from its checkpoint.

        Uses LangGraph's state history to find the checkpoint before
        the failed node and re-invokes from that point.

        Args:
            document_id: Document UUID.
            node_name: Name of the node to retry.

        Returns:
            Final or next-interrupted DocumentState.
        """
        doc_id = str(document_id)
        thread_id = await self._get_thread_id(document_id) or doc_id
        config = {"configurable": {"thread_id": thread_id}}

        logger.info("[runner:%s] Retrying node '%s'", doc_id[:8], node_name)

        # Find the checkpoint just before the failed node
        history = list(self._graph.get_state_history(config))
        target = None
        for snapshot in history:
            if snapshot.next and node_name in snapshot.next:
                target = snapshot
                break

        if target is None:
            logger.error(
                "[runner:%s] No checkpoint found before node '%s'",
                doc_id[:8],
                node_name,
            )
            raise ValueError(f"No checkpoint found before node '{node_name}' for document {doc_id}")

        # Re-invoke from that checkpoint
        result = await self._graph.ainvoke(None, target.config)

        logger.info(
            "[runner:%s] Retry result: status=%s",
            doc_id[:8],
            result.get("status", "unknown"),
        )
        return result

    async def get_status(self, document_id: uuid.UUID) -> dict[str, Any] | None:
        """Get current pipeline state for a document."""
        doc_id = str(document_id)
        thread_id = await self._get_thread_id(document_id) or doc_id
        config = {"configurable": {"thread_id": thread_id}}

        snapshot = self._graph.get_state(config)
        if snapshot and snapshot.values:
            return {
                "status": snapshot.values.get("status"),
                "node_statuses": snapshot.values.get("node_statuses", {}),
                "node_timings": snapshot.values.get("node_timings", {}),
                "next_nodes": list(snapshot.next) if snapshot.next else [],
            }
        return None

    @staticmethod
    async def _save_thread_id(document_id: uuid.UUID, thread_id: str) -> None:
        """Persist the pipeline thread_id on the document record."""
        try:
            from src.db.connection import get_session_factory
            from src.db.repositories.documents import DocumentRepository

            factory = get_session_factory()
            async with factory() as session:
                repo = DocumentRepository(session)
                doc = await repo.get_by_id(document_id)
                if doc:
                    doc.pipeline_thread_id = thread_id
                    doc.status = "processing"
                    await session.commit()
        except Exception as exc:
            logger.error(
                "[runner] Failed to save thread_id for %s: %s",
                document_id,
                exc,
            )

    @staticmethod
    async def _get_thread_id(document_id: uuid.UUID) -> str | None:
        """Read the pipeline thread_id from the document record."""
        try:
            from src.db.connection import get_session_factory
            from src.db.repositories.documents import DocumentRepository

            factory = get_session_factory()
            async with factory() as session:
                repo = DocumentRepository(session)
                doc = await repo.get_by_id(document_id)
                if doc:
                    return doc.pipeline_thread_id
        except Exception as exc:
            logger.warning(
                "[runner] Failed to read thread_id for %s: %s",
                document_id,
                exc,
            )
        return None
