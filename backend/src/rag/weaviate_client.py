"""Weaviate vector store using LangChain integration.

Uses langchain-weaviate for document storage and hybrid search
with OpenAI text-embedding-3-small embeddings.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

try:
    import weaviate
    from langchain_core.documents import Document
    from langchain_openai import OpenAIEmbeddings
    from langchain_weaviate import WeaviateVectorStore
    from weaviate.classes.config import Configure, DataType, Property
    from weaviate.classes.query import Filter

    _WEAVIATE_AVAILABLE = True
except ModuleNotFoundError:
    weaviate = None
    OpenAIEmbeddings = None
    WeaviateVectorStore = None
    Filter = None
    _WEAVIATE_AVAILABLE = False

    @dataclass
    class Document:  # type: ignore[no-redef]
        page_content: str
        metadata: dict[str, Any] | None = None

    @dataclass
    class Property:  # type: ignore[no-redef]
        name: str
        data_type: str

    class DataType:  # type: ignore[no-redef]
        TEXT = "text"
        INT = "int"

    class Configure:  # type: ignore[no-redef]
        class Vectorizer:
            @staticmethod
            def none() -> None:
                return None

logger = logging.getLogger(__name__)

COLLECTION_NAME = "DocumentChunks"
EMBEDDING_MODEL = "text-embedding-3-small"

# Properties the ingestion and query code rely on. Declared explicitly so
# the collection is never left in a half-built state (auto-schema would
# only register the `text` property on its first write, which breaks
# filters like `document_id`).
_COLLECTION_PROPERTIES: list[Property] = [
    Property(name="text", data_type=DataType.TEXT),
    Property(name="document_id", data_type=DataType.TEXT),
    Property(name="document_name", data_type=DataType.TEXT),
    Property(name="document_category", data_type=DataType.TEXT),
    Property(name="file_name", data_type=DataType.TEXT),
    Property(name="chunk_index", data_type=DataType.INT),
    Property(name="header_1", data_type=DataType.TEXT),
    Property(name="header_2", data_type=DataType.TEXT),
    Property(name="header_3", data_type=DataType.TEXT),
]


class _AwaitableValue:
    """Value wrapper that can also be awaited by legacy async tests."""

    def __init__(self, value: Any) -> None:
        self.value = value

    def __await__(self):
        async def _coro():
            return self.value

        return _coro().__await__()


class _AwaitableInt(int):
    def __new__(cls, value: int):
        return int.__new__(cls, value)

    def __await__(self):
        async def _coro():
            return int(self)

        return _coro().__await__()


class _AwaitableList(list):
    def __await__(self):
        async def _coro():
            return self

        return _coro().__await__()


@dataclass
class ChunkData:
    """A chunk payload for in-memory tests and compatibility helpers."""

    text: str
    document_id: str
    document_name: str
    document_category: str
    file_name: str
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class SearchResult:
    """A single search result from Weaviate."""

    chunk_text: str
    document_id: str
    document_name: str
    chunk_index: int
    relevance_score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class WeaviateClient:
    """Client for Weaviate vector database using LangChain integration."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._client: Any | None = None
        self._store: Any | None = None
        self._collections: dict[str, list[ChunkData]] = {}
        self._connected = False
        self._embeddings = (
            OpenAIEmbeddings(model=EMBEDDING_MODEL)
            if _WEAVIATE_AVAILABLE and OpenAIEmbeddings is not None
            else None
        )

    @property
    def is_connected(self) -> bool:
        if not _WEAVIATE_AVAILABLE:
            return self._connected
        return self._client is not None and self._client.is_connected()

    def connect(self) -> _AwaitableValue:
        """Connect to the Weaviate instance."""
        if not _WEAVIATE_AVAILABLE:
            self._connected = True
            self._collections.setdefault(COLLECTION_NAME, [])
            return _AwaitableValue(None)

        if self._client is not None and self._client.is_connected():
            return _AwaitableValue(None)
        logger.info(
            "Connecting to Weaviate at %s (embedding model: %s)",
            self._url,
            EMBEDDING_MODEL,
        )
        self._client = weaviate.connect_to_local(
            host=self._url.replace("http://", "").split(":")[0],
            port=int(self._url.split(":")[-1]) if ":" in self._url.rsplit("/", 1)[-1] else 8080,
        )
        self._ensure_schema()
        self._store = WeaviateVectorStore(
            client=self._client,
            index_name=COLLECTION_NAME,
            text_key="text",
            embedding=self._embeddings,
        )
        return _AwaitableValue(None)

    def _ensure_schema(self) -> None:
        """Ensure DocumentChunks has the expected properties.

        Creates the collection if missing. If the collection exists but
        lacks any of the expected properties (e.g. it was auto-created by
        langchain-weaviate with only ``text``), the missing properties are
        added. The collection is only recreated when it is empty and its
        schema diverges — never when it already holds ingested data.
        """
        assert self._client is not None
        existing_names: set[str] = set()
        if self._client.collections.exists(COLLECTION_NAME):
            collection = self._client.collections.get(COLLECTION_NAME)
            config = collection.config.get()
            existing_names = {p.name for p in config.properties}

            missing = [p for p in _COLLECTION_PROPERTIES if p.name not in existing_names]
            if not missing:
                return

            if collection.aggregate.over_all(total_count=True).total_count:
                logger.info(
                    "Collection %s missing %d properties (%s); adding in place",
                    COLLECTION_NAME,
                    len(missing),
                    [p.name for p in missing],
                )
                for prop in missing:
                    collection.config.add_property(prop)
                return

            logger.info(
                "Collection %s is empty and missing properties (%s); recreating with full schema",
                COLLECTION_NAME,
                [p.name for p in missing],
            )
            self._client.collections.delete(COLLECTION_NAME)

        logger.info("Creating Weaviate collection %s with explicit schema", COLLECTION_NAME)
        self._client.collections.create(
            name=COLLECTION_NAME,
            properties=_COLLECTION_PROPERTIES,
            vectorizer_config=Configure.Vectorizer.none(),
        )

    def disconnect(self) -> _AwaitableValue:
        """Disconnect from Weaviate."""
        if not _WEAVIATE_AVAILABLE:
            self._connected = False
            return _AwaitableValue(None)

        if self._client is not None:
            self._client.close()
            self._client = None
            self._store = None
            logger.info("Disconnected from Weaviate")
        return _AwaitableValue(None)

    def _ensure_connected(self) -> WeaviateVectorStore:
        """Ensure connected and return the vector store."""
        if not _WEAVIATE_AVAILABLE:
            self.connect()
            return None  # type: ignore[return-value]

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
        if not _WEAVIATE_AVAILABLE:
            chunks = [
                ChunkData(
                    text=text,
                    document_id=str(meta.get("document_id", "")),
                    document_name=str(meta.get("document_name", "")),
                    document_category=str(meta.get("document_category", "")),
                    file_name=str(meta.get("file_name", "")),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    metadata=meta,
                )
                for text, meta in zip(texts, metadatas)
            ]
            self._collections.setdefault(COLLECTION_NAME, []).extend(chunks)
            return len(chunks)

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

    def delete_by_document(self, document_id: str) -> _AwaitableInt:
        """Delete all chunks for a document. No-op if collection/property doesn't exist yet."""
        self._ensure_connected()
        if not _WEAVIATE_AVAILABLE:
            chunks = self._collections.setdefault(COLLECTION_NAME, [])
            before = len(chunks)
            self._collections[COLLECTION_NAME] = [
                chunk for chunk in chunks if chunk.document_id != document_id
            ]
            return _AwaitableInt(before - len(self._collections[COLLECTION_NAME]))

        assert self._client is not None

        if not self._client.collections.exists(COLLECTION_NAME):
            return _AwaitableInt(0)

        try:
            collection = self._client.collections.get(COLLECTION_NAME)
            collection.data.delete_many(
                where=Filter.by_property("document_id").equal(document_id)
            )
            logger.info(
                "Deleted existing chunks for document %s from %s",
                document_id,
                COLLECTION_NAME,
            )
            return _AwaitableInt(0)
        except Exception as exc:
            if "no such prop" in str(exc):
                logger.info(
                    "Collection %s has no document_id property yet; skipping delete",
                    COLLECTION_NAME,
                )
            else:
                raise
        return _AwaitableInt(0)

    def search(
        self,
        query: str,
        top_k: int = 5,
        alpha: float = 0.5,
        document_id: str | None = None,
        category: str | None = None,
    ) -> _AwaitableList:
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
        if not _WEAVIATE_AVAILABLE:
            chunks = self._collections.setdefault(COLLECTION_NAME, [])
            matches = []
            terms = [term.casefold() for term in query.split() if term.strip()]
            for chunk in chunks:
                if document_id and chunk.document_id != document_id:
                    continue
                if category and chunk.document_category != category:
                    continue
                if terms and not any(term in chunk.text.casefold() for term in terms):
                    continue
                matches.append(
                    SearchResult(
                        chunk_text=chunk.text,
                        document_id=chunk.document_id,
                        document_name=chunk.document_name,
                        chunk_index=chunk.chunk_index,
                        relevance_score=1.0,
                        metadata={
                            **chunk.metadata,
                            "document_id": chunk.document_id,
                            "document_name": chunk.document_name,
                            "document_category": chunk.document_category,
                            "file_name": chunk.file_name,
                            "chunk_index": chunk.chunk_index,
                        },
                    )
                )
            return _AwaitableList(matches[:top_k])

        filters = None
        if document_id:
            filters = Filter.by_property("document_id").equal(document_id)
        elif category:
            filters = Filter.by_property("document_category").equal(category)

        results = store.similarity_search_with_score(
            query, k=top_k, alpha=alpha, filters=filters
        )

        search_results = _AwaitableList()
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

    def get_chunk_count(self, document_id: str) -> _AwaitableInt:
        """Count chunks for a document."""
        if not _WEAVIATE_AVAILABLE:
            return _AwaitableInt(
                sum(
                    1
                    for chunk in self._collections.setdefault(COLLECTION_NAME, [])
                    if chunk.document_id == document_id
                )
            )

        assert self._client is not None
        collection = self._client.collections.get(COLLECTION_NAME)
        result = collection.aggregate.over_all(
            filters=Filter.by_property("document_id").equal(document_id),
            total_count=True,
        )
        return _AwaitableInt(result.total_count or 0)

    def create_collection(self, name: str) -> _AwaitableValue:
        """Create an in-memory collection for legacy tests."""
        if not _WEAVIATE_AVAILABLE:
            self._collections.setdefault(name, [])
            return _AwaitableValue(None)
        self.connect()
        assert self._client is not None
        if not self._client.collections.exists(name):
            self._client.collections.create(name=name)
        return _AwaitableValue(None)

    def upsert_chunks(self, chunks: list[ChunkData]) -> _AwaitableInt:
        """Insert chunks via the in-memory compatibility API."""
        if not _WEAVIATE_AVAILABLE:
            self._collections.setdefault(COLLECTION_NAME, []).extend(chunks)
            return _AwaitableInt(len(chunks))
        return _AwaitableInt(
            self.add_documents(
                [chunk.text for chunk in chunks],
                [
                    {
                        "document_id": chunk.document_id,
                        "document_name": chunk.document_name,
                        "document_category": chunk.document_category,
                        "file_name": chunk.file_name,
                        "chunk_index": chunk.chunk_index,
                        **chunk.metadata,
                    }
                    for chunk in chunks
                ],
            )
        )
