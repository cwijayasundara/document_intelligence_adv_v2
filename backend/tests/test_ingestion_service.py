"""Tests for the ingestion service."""

from __future__ import annotations

import uuid

from src.rag.chunker import Chunk, DocumentChunker
from src.services.ingest_service import IngestionService


class FakeWeaviateClient:
    """Minimal in-memory Weaviate test double."""

    def __init__(self) -> None:
        self.deleted_ids: list[str] = []
        self.texts: list[str] = []
        self.metadatas: list[dict] = []

    def delete_by_document(self, document_id: str) -> None:
        self.deleted_ids.append(document_id)
        self.metadatas = [m for m in self.metadatas if m["document_id"] != document_id]

    def add_documents(self, texts: list[str], metadatas: list[dict]) -> int:
        self.texts.extend(texts)
        self.metadatas.extend(metadatas)
        return len(texts)


class TestIngestionService:
    """Tests for IngestionService."""

    def setup_method(self) -> None:
        self.weaviate = FakeWeaviateClient()
        self.chunker = DocumentChunker(max_tokens=50, overlap_tokens=10, chars_per_token=4)
        self.service = IngestionService(weaviate_client=self.weaviate, chunker=self.chunker)

    def test_ingest_document(self) -> None:
        doc_id = uuid.uuid4()
        chunks = self.service.ingest_document(
            document_id=doc_id,
            document_name="test.pdf",
            document_category="LPA",
            file_name="test.pdf",
            parsed_content="Hello world. This is a test.",
        )

        assert chunks >= 1
        assert self.weaviate.deleted_ids == [str(doc_id)]
        assert self.weaviate.metadatas[0]["document_id"] == str(doc_id)

    def test_ingest_creates_chunks(self) -> None:
        doc_id = uuid.uuid4()
        content = "Paragraph one. " * 50 + "\n\n" + "Paragraph two. " * 50

        chunks = self.service.ingest_document(
            document_id=doc_id,
            document_name="test.pdf",
            document_category="LPA",
            file_name="test.pdf",
            parsed_content=content,
        )

        assert chunks > 1

    def test_reingest_deletes_old_chunks(self) -> None:
        doc_id = uuid.uuid4()
        self.service.ingest_document(
            document_id=doc_id,
            document_name="test.pdf",
            document_category="LPA",
            file_name="test.pdf",
            parsed_content="Content v1. " * 50,
        )

        self.service.ingest_document(
            document_id=doc_id,
            document_name="test.pdf",
            document_category="LPA",
            file_name="test.pdf",
            parsed_content="Content v2. " * 50,
        )

        assert self.weaviate.deleted_ids == [str(doc_id), str(doc_id)]
        assert self.weaviate.metadatas

    def test_ingest_empty_content(self) -> None:
        doc_id = uuid.uuid4()
        chunks = self.service.ingest_document(
            document_id=doc_id,
            document_name="empty.pdf",
            document_category="Other",
            file_name="empty.pdf",
            parsed_content="",
        )

        assert chunks == 0

    def test_ingest_uses_default_chunker(self) -> None:
        service = IngestionService(weaviate_client=self.weaviate)
        doc_id = uuid.uuid4()

        chunks = service.ingest_document(
            document_id=doc_id,
            document_name="test.pdf",
            document_category="LPA",
            file_name="test.pdf",
            parsed_content="Some test content.",
        )

        assert chunks >= 1

    def test_ingest_uses_precomputed_reducto_chunks(self) -> None:
        doc_id = uuid.uuid4()
        precomputed = [
            Chunk(text="Reducto chunk", index=0, metadata={"provider": "reducto", "page": "1"})
        ]

        chunks = self.service.ingest_document(
            document_id=doc_id,
            document_name="test.pdf",
            document_category="LPA",
            file_name="test.pdf",
            parsed_content="",
            chunks=precomputed,
        )

        assert chunks == 1
        assert self.weaviate.texts == ["Reducto chunk"]
        assert self.weaviate.metadatas[0]["provider"] == "reducto"
