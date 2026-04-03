"""Weaviate vector store using LangChain integration.

Uses langchain-weaviate for document storage and hybrid search
with OpenAI text-embedding-3-small embeddings.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import weaviate
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_weaviate import WeaviateVectorStore
from weaviate.classes.query import Filter

logger = logging.getLogger(__name__)

COLLECTION_NAME = "DocumentChunks"
EMBEDDING_MODEL = "text-embedding-3-small"


@dataclass
class SearchResult:
    """A single search result from Weaviate."""

    chunk_text: str
    document_id: str
    document_name: str
    chunk_index: int
    relevance_score: float
    metadata: dict[str, Any]


class WeaviateClient:
    """Client for Weaviate vector database using LangChain integration."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._client: weaviate.WeaviateClient | None = None
        self._store: WeaviateVectorStore | None = None
        self._embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected()

    def connect(self) -> None:
        """Connect to the Weaviate instance."""
        if self._client is not None and self._client.is_connected():
            return
        logger.info(
            "Connecting to Weaviate at %s (embedding model: %s)",
            self._url,
            EMBEDDING_MODEL,
        )
        self._client = weaviate.connect_to_local(
            host=self._url.replace("http://", "").split(":")[0],
            port=int(self._url.split(":")[-1]) if ":" in self._url.rsplit("/", 1)[-1] else 8080,
        )
        self._store = WeaviateVectorStore(
            client=self._client,
            index_name=COLLECTION_NAME,
            text_key="text",
            embedding=self._embeddings,
        )

    def disconnect(self) -> None:
        """Disconnect from Weaviate."""
        if self._client is not None:
            self._client.close()
            self._client = None
            self._store = None
            logger.info("Disconnected from Weaviate")

    def _ensure_connected(self) -> WeaviateVectorStore:
        """Ensure connected and return the vector store."""
        if self._store is None:
            self.connect()
        assert self._store is not None
        return self._store

    def add_documents(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]],
    ) -> int:
        """Add document chunks with metadata to Weaviate.

        Args:
            texts: List of chunk text contents.
            metadatas: List of metadata dicts per chunk.

        Returns:
            Number of chunks added.
        """
        store = self._ensure_connected()
        docs = [
            Document(page_content=text, metadata=meta)
            for text, meta in zip(texts, metadatas)
        ]
        logger.info(
            "Generating embeddings and storing %d chunks in %s (model: %s)",
            len(docs),
            COLLECTION_NAME,
            EMBEDDING_MODEL,
        )
        store.add_documents(docs)
        logger.info("Successfully stored %d chunks with embeddings", len(docs))
        return len(docs)

    def delete_by_document(self, document_id: str) -> None:
        """Delete all chunks for a document. No-op if collection/property doesn't exist yet."""
        self._ensure_connected()
        assert self._client is not None

        if not self._client.collections.exists(COLLECTION_NAME):
            return

        try:
            collection = self._client.collections.get(COLLECTION_NAME)
            collection.data.delete_many(
                where=Filter.by_property("document_id").equal(document_id)
            )
            logger.info("Deleted existing chunks for document %s from %s", document_id, COLLECTION_NAME)
        except Exception as exc:
            if "no such prop" in str(exc):
                logger.info(
                    "Collection %s has no document_id property yet (first ingestion), skipping delete",
                    COLLECTION_NAME,
                )
            else:
                raise

    def search(
        self,
        query: str,
        top_k: int = 5,
        alpha: float = 0.5,
        document_id: str | None = None,
        category: str | None = None,
    ) -> list[SearchResult]:
        """Hybrid search for relevant chunks.

        Args:
            query: Search query text.
            top_k: Number of results to return.
            alpha: Balance between keyword (0) and vector (1) search.
            document_id: Optional filter by document ID.
            category: Optional filter by document category.

        Returns:
            List of SearchResult objects.
        """
        store = self._ensure_connected()

        filters = None
        if document_id:
            filters = Filter.by_property("document_id").equal(document_id)
        elif category:
            filters = Filter.by_property("document_category").equal(category)

        results = store.similarity_search_with_score(
            query, k=top_k, alpha=alpha, filters=filters
        )

        search_results = []
        for doc, score in results:
            meta = doc.metadata or {}
            search_results.append(
                SearchResult(
                    chunk_text=doc.page_content,
                    document_id=meta.get("document_id", ""),
                    document_name=meta.get("document_name", ""),
                    chunk_index=meta.get("chunk_index", 0),
                    relevance_score=score,
                    metadata=meta,
                )
            )
        return search_results

    def get_chunk_count(self, document_id: str) -> int:
        """Count chunks for a document."""
        assert self._client is not None
        collection = self._client.collections.get(COLLECTION_NAME)
        result = collection.aggregate.over_all(
            filters=Filter.by_property("document_id").equal(document_id),
            total_count=True,
        )
        return result.total_count or 0
