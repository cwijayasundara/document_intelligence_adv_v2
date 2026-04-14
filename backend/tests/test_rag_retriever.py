"""Tests for RAG retriever functions and RAG service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.rag.weaviate_client import ChunkData, SearchResult, WeaviateClient
from src.services.rag_service import SEARCH_MODE_ALPHA, RAGService


class TestRetrieveChunks:
    """Tests for the retrieve_chunks function."""

    @pytest.mark.asyncio
    async def test_retrieve_returns_results(self) -> None:
        """Test basic retrieval returns search results."""
        weaviate = WeaviateClient(url="http://test:8080")
        await weaviate.connect()
        await weaviate.upsert_chunks(
            [
                ChunkData(
                    text="Management fee is 2%",
                    document_id="doc-1",
                    document_name="sample-lpa.pdf",
                    document_category="LPA",
                    file_name="sample-lpa.pdf",
                    chunk_index=0,
                )
            ]
        )

        from src.agents.rag_retriever import retrieve_chunks

        results = retrieve_chunks(weaviate, query="management fee", top_k=5, document_id="doc-1")
        assert len(results) == 1
        assert results[0].chunk_text == "Management fee is 2%"

    @pytest.mark.asyncio
    async def test_retrieve_empty_collection(self) -> None:
        """Test retrieval from empty collection."""
        weaviate = WeaviateClient(url="http://test:8080")
        await weaviate.connect()

        from src.agents.rag_retriever import retrieve_chunks

        results = retrieve_chunks(weaviate, query="test", top_k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_generate_answer(self) -> None:
        """Test answer generation from chunks via LLM."""
        chunks = [
            SearchResult(
                chunk_text="The fee is 2% per annum",
                document_id="doc-1",
                document_name="lpa.pdf",
                chunk_index=0,
                relevance_score=0.9,
            )
        ]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "The fee is 2% per annum based on the LPA."

        with patch("src.agents.rag_retriever.AsyncOpenAI") as mock_openai_cls:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai_cls.return_value = mock_client

            from src.agents.rag_retriever import generate_answer

            answer = await generate_answer("What is the fee?", chunks)

        assert isinstance(answer, str)
        assert len(answer) > 0


class TestRAGService:
    """Tests for RAG service orchestration."""

    @pytest.mark.asyncio
    async def test_query_single_document(self) -> None:
        """Test querying scoped to a single document."""
        weaviate = WeaviateClient(url="http://test:8080")
        await weaviate.connect()
        await weaviate.upsert_chunks(
            [
                ChunkData(
                    text="Commitment period is 5 years",
                    document_id="doc-1",
                    document_name="lpa.pdf",
                    document_category="LPA",
                    file_name="lpa.pdf",
                    chunk_index=0,
                )
            ]
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Commitment period is 5 years."

        with patch("src.agents.rag_retriever.AsyncOpenAI") as mock_openai_cls:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai_cls.return_value = mock_client

            service = RAGService(weaviate_client=weaviate)
            result = await service.query(
                query="commitment period",
                scope="single_document",
                scope_id="doc-1",
                search_mode="hybrid",
                top_k=5,
            )

        assert "answer" in result
        assert "citations" in result
        assert result["search_mode"] == "hybrid"
        assert result["chunks_retrieved"] >= 0

    @pytest.mark.asyncio
    async def test_query_all_scope(self) -> None:
        """Test querying across all documents."""
        weaviate = WeaviateClient(url="http://test:8080")
        await weaviate.connect()

        service = RAGService(weaviate_client=weaviate)
        result = await service.query(
            query="test query",
            scope="all",
            search_mode="semantic",
        )
        assert result["search_mode"] == "semantic"

    def test_search_mode_alpha_values(self) -> None:
        """Test alpha mapping for search modes."""
        assert SEARCH_MODE_ALPHA["keyword"] == 0.0
        assert SEARCH_MODE_ALPHA["hybrid"] == 0.5
        assert SEARCH_MODE_ALPHA["semantic"] == 1.0
