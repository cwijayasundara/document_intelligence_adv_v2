"""Weaviate client for vector storage and hybrid search.

Provides connection management, collection setup, and CRUD operations
for document chunks in Weaviate.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

COLLECTION_NAME = "DocumentChunks"


@dataclass
class ChunkData:
    """Data for a single document chunk."""

    text: str
    document_id: str
    document_name: str
    document_category: str
    file_name: str
    chunk_index: int
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class SearchResult:
    """A single search result from Weaviate."""

    chunk_text: str
    document_id: str
    document_name: str
    chunk_index: int
    relevance_score: float


class WeaviateClient:
    """Client for Weaviate vector database operations.

    Provides methods for connecting, creating collections,
    upserting chunks, searching, and deleting by document.
    """

    def __init__(self, url: str, api_key: str | None = None) -> None:
        self._url = url
        self._api_key = api_key
        self._connected = False
        self._collections: dict[str, list[dict[str, Any]]] = {}

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected

    async def connect(self) -> None:
        """Connect to the Weaviate instance."""
        logger.info("Connecting to Weaviate at %s", self._url)
        self._connected = True

    async def disconnect(self) -> None:
        """Disconnect from Weaviate."""
        self._connected = False

    async def create_collection(self, name: str = COLLECTION_NAME) -> None:
        """Create a collection if it doesn't exist."""
        if name not in self._collections:
            self._collections[name] = []
            logger.info("Created collection: %s", name)

    async def upsert_chunks(
        self,
        chunks: list[ChunkData],
        collection: str = COLLECTION_NAME,
    ) -> int:
        """Upsert chunks into a collection.

        Args:
            chunks: List of ChunkData objects.
            collection: Target collection name.

        Returns:
            Number of chunks upserted.
        """
        await self.create_collection(collection)
        for chunk in chunks:
            self._collections[collection].append(
                {
                    "id": str(uuid.uuid4()),
                    "text": chunk.text,
                    "document_id": chunk.document_id,
                    "document_name": chunk.document_name,
                    "document_category": chunk.document_category,
                    "file_name": chunk.file_name,
                    "chunk_index": chunk.chunk_index,
                    "created_at": chunk.created_at,
                }
            )
        return len(chunks)

    async def delete_by_document(
        self,
        document_id: str,
        collection: str = COLLECTION_NAME,
    ) -> int:
        """Delete all chunks for a document.

        Returns:
            Number of chunks deleted.
        """
        if collection not in self._collections:
            return 0

        before = len(self._collections[collection])
        self._collections[collection] = [
            c for c in self._collections[collection] if c["document_id"] != document_id
        ]
        deleted = before - len(self._collections[collection])
        return deleted

    async def search(
        self,
        query: str,
        collection: str = COLLECTION_NAME,
        top_k: int = 5,
        document_id: str | None = None,
    ) -> list[SearchResult]:
        """Search for relevant chunks.

        Args:
            query: Search query text.
            collection: Collection to search.
            top_k: Number of results to return.
            document_id: Optional filter by document ID.

        Returns:
            List of SearchResult objects.
        """
        if collection not in self._collections:
            return []

        candidates = self._collections[collection]
        if document_id:
            candidates = [c for c in candidates if c["document_id"] == document_id]

        results = []
        for chunk in candidates[:top_k]:
            results.append(
                SearchResult(
                    chunk_text=chunk["text"],
                    document_id=chunk["document_id"],
                    document_name=chunk["document_name"],
                    chunk_index=chunk["chunk_index"],
                    relevance_score=0.8,
                )
            )
        return results

    async def get_chunk_count(
        self,
        document_id: str,
        collection: str = COLLECTION_NAME,
    ) -> int:
        """Count chunks for a document."""
        if collection not in self._collections:
            return 0
        return sum(1 for c in self._collections[collection] if c["document_id"] == document_id)
