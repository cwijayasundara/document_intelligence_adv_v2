"""Tests for the Weaviate client."""

import pytest

from src.rag.weaviate_client import ChunkData, WeaviateClient


class TestWeaviateClient:
    """Tests for WeaviateClient."""

    def setup_method(self) -> None:
        self.client = WeaviateClient(url="http://localhost:8080")

    @pytest.mark.asyncio
    async def test_connect(self) -> None:
        await self.client.connect()
        assert self.client.is_connected is True

    @pytest.mark.asyncio
    async def test_disconnect(self) -> None:
        await self.client.connect()
        await self.client.disconnect()
        assert self.client.is_connected is False

    @pytest.mark.asyncio
    async def test_create_collection(self) -> None:
        await self.client.create_collection("TestCollection")
        assert "TestCollection" in self.client._collections

    @pytest.mark.asyncio
    async def test_create_collection_idempotent(self) -> None:
        await self.client.create_collection("TestCollection")
        await self.client.create_collection("TestCollection")
        assert "TestCollection" in self.client._collections

    @pytest.mark.asyncio
    async def test_upsert_chunks(self) -> None:
        chunks = [
            ChunkData(
                text="Hello world",
                document_id="doc-1",
                document_name="test.pdf",
                document_category="LPA",
                file_name="test.pdf",
                chunk_index=0,
            ),
        ]
        count = await self.client.upsert_chunks(chunks)
        assert count == 1

    @pytest.mark.asyncio
    async def test_upsert_multiple_chunks(self) -> None:
        chunks = [
            ChunkData(
                text=f"Chunk {i}",
                document_id="doc-1",
                document_name="test.pdf",
                document_category="LPA",
                file_name="test.pdf",
                chunk_index=i,
            )
            for i in range(5)
        ]
        count = await self.client.upsert_chunks(chunks)
        assert count == 5

    @pytest.mark.asyncio
    async def test_delete_by_document(self) -> None:
        chunks = [
            ChunkData(
                text="Hello",
                document_id="doc-1",
                document_name="test.pdf",
                document_category="LPA",
                file_name="test.pdf",
                chunk_index=0,
            ),
            ChunkData(
                text="World",
                document_id="doc-2",
                document_name="other.pdf",
                document_category="LPA",
                file_name="other.pdf",
                chunk_index=0,
            ),
        ]
        await self.client.upsert_chunks(chunks)
        deleted = await self.client.delete_by_document("doc-1")
        assert deleted == 1

    @pytest.mark.asyncio
    async def test_delete_nonexistent_document(self) -> None:
        deleted = await self.client.delete_by_document("nonexistent")
        assert deleted == 0

    @pytest.mark.asyncio
    async def test_search(self) -> None:
        chunks = [
            ChunkData(
                text="Management fee is 2%",
                document_id="doc-1",
                document_name="test.pdf",
                document_category="LPA",
                file_name="test.pdf",
                chunk_index=0,
            ),
        ]
        await self.client.upsert_chunks(chunks)
        results = await self.client.search("management fee")
        assert len(results) >= 1
        assert results[0].chunk_text == "Management fee is 2%"

    @pytest.mark.asyncio
    async def test_search_with_document_filter(self) -> None:
        chunks = [
            ChunkData(
                text="Doc 1 content",
                document_id="doc-1",
                document_name="a.pdf",
                document_category="LPA",
                file_name="a.pdf",
                chunk_index=0,
            ),
            ChunkData(
                text="Doc 2 content",
                document_id="doc-2",
                document_name="b.pdf",
                document_category="LPA",
                file_name="b.pdf",
                chunk_index=0,
            ),
        ]
        await self.client.upsert_chunks(chunks)
        results = await self.client.search("content", document_id="doc-1")
        assert len(results) == 1
        assert results[0].document_id == "doc-1"

    @pytest.mark.asyncio
    async def test_search_empty_collection(self) -> None:
        results = await self.client.search("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_get_chunk_count(self) -> None:
        chunks = [
            ChunkData(
                text=f"Chunk {i}",
                document_id="doc-1",
                document_name="test.pdf",
                document_category="LPA",
                file_name="test.pdf",
                chunk_index=i,
            )
            for i in range(3)
        ]
        await self.client.upsert_chunks(chunks)
        count = await self.client.get_chunk_count("doc-1")
        assert count == 3

    @pytest.mark.asyncio
    async def test_get_chunk_count_nonexistent(self) -> None:
        count = await self.client.get_chunk_count("nonexistent")
        assert count == 0

    def test_chunk_data_auto_created_at(self) -> None:
        chunk = ChunkData(
            text="test",
            document_id="doc-1",
            document_name="test.pdf",
            document_category="LPA",
            file_name="test.pdf",
            chunk_index=0,
        )
        assert chunk.created_at != ""
