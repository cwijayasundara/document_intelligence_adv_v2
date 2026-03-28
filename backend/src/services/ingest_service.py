"""Ingestion service for chunking and upserting documents to Weaviate."""

from __future__ import annotations

import uuid

from src.rag.chunker import SemanticChunker
from src.rag.weaviate_client import ChunkData, WeaviateClient


class IngestionService:
    """Orchestrate document chunking and Weaviate ingestion."""

    def __init__(
        self,
        weaviate_client: WeaviateClient,
        chunker: SemanticChunker | None = None,
    ) -> None:
        self._weaviate = weaviate_client
        self._chunker = chunker or SemanticChunker()

    async def ingest_document(
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

        await self._weaviate.delete_by_document(doc_id_str)

        chunks = self._chunker.chunk(parsed_content)

        chunk_data = [
            ChunkData(
                text=chunk.text,
                document_id=doc_id_str,
                document_name=document_name,
                document_category=document_category,
                file_name=file_name,
                chunk_index=chunk.index,
            )
            for chunk in chunks
        ]

        if chunk_data:
            await self._weaviate.upsert_chunks(chunk_data)

        return len(chunk_data)
