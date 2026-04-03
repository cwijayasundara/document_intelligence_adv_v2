"""Ingestion service for chunking and upserting documents to Weaviate."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from src.rag.chunker import DocumentChunker
from src.rag.weaviate_client import WeaviateClient

logger = logging.getLogger(__name__)


class IngestionService:
    """Orchestrate document chunking and Weaviate ingestion."""

    def __init__(
        self,
        weaviate_client: WeaviateClient,
        chunker: DocumentChunker | None = None,
    ) -> None:
        self._weaviate = weaviate_client
        self._chunker = chunker or DocumentChunker()

    def ingest_document(
        self,
        document_id: uuid.UUID,
        document_name: str,
        document_category: str,
        file_name: str,
        parsed_content: str,
    ) -> int:
        """Chunk and ingest a document into Weaviate.

        Deletes existing chunks for the document before re-inserting.

        Args:
            document_id: UUID of the document.
            document_name: Display name.
            document_category: Category name.
            file_name: Original file name.
            parsed_content: Parsed markdown content.

        Returns:
            Number of chunks created.
        """
        doc_id_str = str(document_id)

        logger.info(
            "Starting ingestion pipeline for '%s' (id=%s, category=%s, %d chars)",
            file_name,
            document_id,
            document_category or "uncategorized",
            len(parsed_content),
        )

        logger.info("Step 1/3: Removing previous chunks for document %s", document_id)
        self._weaviate.delete_by_document(doc_id_str)

        logger.info("Step 2/3: Chunking document with markdown-aware splitter")
        chunks = self._chunker.chunk(parsed_content)

        if not chunks:
            logger.warning("No chunks generated for document %s — content may be empty", document_id)
            return 0

        texts = [c.text for c in chunks]
        metadatas: list[dict[str, Any]] = [
            {
                "document_id": doc_id_str,
                "document_name": document_name,
                "document_category": document_category,
                "file_name": file_name,
                "chunk_index": c.index,
                **c.metadata,
            }
            for c in chunks
        ]

        logger.info(
            "Step 3/3: Embedding and storing %d chunks in Weaviate (metadata: document_id, file_name, category, headers)",
            len(chunks),
        )
        count = self._weaviate.add_documents(texts, metadatas)

        logger.info(
            "Ingestion complete for '%s': %d chunks stored in vector DB",
            file_name,
            count,
        )
        return count
