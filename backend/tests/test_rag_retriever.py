"""Tests for RAG retriever subagent and RAG service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.rag.weaviate_client import ChunkData, SearchResult, WeaviateClient
from src.services.rag_service import SEARCH_MODE_ALPHA, RAGService


class TestRAGRetrieverSubagent:
    """Tests for the RAG retriever subagent."""

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

        with patch("src.agents.rag_retriever.create_deep_agent") as mock_create:
            mock_create.return_value = MagicMock()
            from src.agents.rag_retriever import RAGRetrieverSubagent

            retriever = RAGRetrieverSubagent(weaviate)

        results = await retriever.retrieve(query="management fee", top_k=5, document_id="doc-1")
        assert len(results) == 1
        assert results[0].chunk_text == "Management fee is 2%"

    @pytest.mark.asyncio
    async def test_retrieve_empty_collection(self) -> None:
        """Test retrieval from empty collection."""
        weaviate = WeaviateClient(url="http://test:8080")
        await weaviate.connect()

        with patch("src.agents.rag_retriever.create_deep_agent") as mock_create:
            mock_create.return_value = MagicMock()
            from src.agents.rag_retriever import RAGRetrieverSubagent

            retriever = RAGRetrieverSubagent(weaviate)

        results = await retriever.retrieve(query="test", top_k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_generate_answer(self) -> None:
        """Test answer generation from chunks via LLM."""
        weaviate = WeaviateClient(url="http://test:8080")
        await weaviate.connect()

        from unittest.mock import AsyncMock

        with patch("src.agents.rag_retriever.create_deep_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(
                return_value={
                    "response": "The fee is 2% per annum based on the LPA.",
                }
            )
            mock_create.return_value = mock_agent
            from src.agents.rag_retriever import RAGRetrieverSubagent

            retriever = RAGRetrieverSubagent(weaviate)

        chunks = [
            SearchResult(
                chunk_text="The fee is 2% per annum",
                document_id="doc-1",
                document_name="lpa.pdf",
                chunk_index=0,
                relevance_score=0.9,
            )
        ]

        answer = await retriever.generate_answer("What is the fee?", chunks)
        assert isinstance(answer, str)
        assert len(answer) > 0

    @pytest.mark.asyncio
    async def test_search_tool(self) -> None:
        """Test the _search_documents tool method."""
        weaviate = WeaviateClient(url="http://test:8080")
        await weaviate.connect()
        await weaviate.upsert_chunks(
            [
                ChunkData(
                    text="Fund term is 10 years",
                    document_id="doc-2",
                    document_name="lpa.pdf",
                    document_category="LPA",
                    file_name="lpa.pdf",
                    chunk_index=1,
                )
            ]
        )

        with patch("src.agents.rag_retriever.create_deep_agent") as mock_create:
            mock_create.return_value = MagicMock()
            from src.agents.rag_retriever import RAGRetrieverSubagent

            retriever = RAGRetrieverSubagent(weaviate)

        results = await retriever._search_documents("fund term", top_k=3)
        assert len(results) == 1
        assert results[0]["chunk_text"] == "Fund term is 10 years"

    def test_as_subagent_config(self) -> None:
        """Test subagent config creation."""
        weaviate = WeaviateClient(url="http://test:8080")
        with patch("src.agents.rag_retriever.create_deep_agent") as mock_create:
            mock_create.return_value = MagicMock()
            from src.agents.rag_retriever import RAGRetrieverSubagent

            retriever = RAGRetrieverSubagent(weaviate)

        config = retriever.as_subagent_config()
        assert config["name"] == "rag_retriever"
        assert isinstance(config, dict)


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

        mock_agent = MagicMock()
        mock_agent.ainvoke = AsyncMock(return_value={"response": "Commitment period is 5 years."})
        with patch("src.agents.rag_retriever.create_deep_agent", return_value=mock_agent):
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

        mock_agent = MagicMock()
        mock_agent.ainvoke = AsyncMock(return_value={"response": "No results."})
        with patch("src.agents.rag_retriever.create_deep_agent", return_value=mock_agent):
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
