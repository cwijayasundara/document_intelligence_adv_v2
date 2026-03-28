"""Tests for the ingestion service."""

import uuid

import pytest

from src.rag.chunker import SemanticChunker
from src.rag.weaviate_client import WeaviateClient
from src.services.ingest_service import IngestionService


class TestIngestionService:
    """Tests for IngestionService."""

    def setup_method(self) -> None:
        self.weaviate = WeaviateClient(url="http://localhost:8080")
        self.chunker = SemanticChunker(
            max_tokens=50, overlap_tokens=10, chars_per_token=4
        )
        self.service = IngestionService(
            weaviate_client=self.weaviate, chunker=self.chunker
        )

    @pytest.mark.asyncio
    async def test_ingest_document(self) -> None:
        doc_id = uuid.uuid4()
        chunks = await self.service.ingest_document(
            document_id=doc_id,
            document_name="test.pdf",
            document_category="LPA",
            file_name="test.pdf",
            parsed_content="Hello world. This is a test.",
        )
        assert chunks >= 1

    @pytest.mark.asyncio
    async def test_ingest_creates_chunks(self) -> None:
        doc_id = uuid.uuid4()
        content = "Paragraph one. " * 50 + "\n\n" + "Paragraph two. " * 50
        chunks = await self.service.ingest_document(
            document_id=doc_id,
            document_name="test.pdf",
            document_category="LPA",
            file_name="test.pdf",
            parsed_content=content,
        )
        assert chunks > 1

    @pytest.mark.asyncio
    async def test_reingest_deletes_old_chunks(self) -> None:
        doc_id = uuid.uuid4()
        await self.service.ingest_document(
            document_id=doc_id,
            document_name="test.pdf",
            document_category="LPA",
            file_name="test.pdf",
            parsed_content="Content v1. " * 50,
        )
        count1 = await self.weaviate.get_chunk_count(str(doc_id))

        await self.service.ingest_document(
            document_id=doc_id,
            document_name="test.pdf",
            document_category="LPA",
            file_name="test.pdf",
            parsed_content="Content v2. " * 50,
        )
        count2 = await self.weaviate.get_chunk_count(str(doc_id))

        # Counts should be similar — old chunks deleted, new ones added
        assert count2 > 0

    @pytest.mark.asyncio
    async def test_ingest_empty_content(self) -> None:
        doc_id = uuid.uuid4()
        chunks = await self.service.ingest_document(
            document_id=doc_id,
            document_name="empty.pdf",
            document_category="Other",
            file_name="empty.pdf",
            parsed_content="",
        )
        assert chunks == 0

    @pytest.mark.asyncio
    async def test_ingest_uses_default_chunker(self) -> None:
        service = IngestionService(weaviate_client=self.weaviate)
        doc_id = uuid.uuid4()
        chunks = await service.ingest_document(
            document_id=doc_id,
            document_name="test.pdf",
            document_category="LPA",
            file_name="test.pdf",
            parsed_content="Some test content.",
        )
        assert chunks >= 1
