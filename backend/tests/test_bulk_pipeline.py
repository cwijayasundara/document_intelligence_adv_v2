"""Tests for the LangGraph bulk processing pipeline."""

from __future__ import annotations

import sys
import types
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bulk.nodes import (
    classify_node,
    extract_node,
    finalize_node,
    ingest_node,
    parse_node,
    summarize_node,
)
from src.bulk.pipeline import (
    build_pipeline,
    create_checkpointer,
    run_bulk_pipeline,
    run_pipeline_for_document,
)
from src.bulk.state import DocumentState
from src.config.settings import ChunkingSettings, ProcessingSettings, StorageSettings
from src.graph_nodes.schemas.classification import ClassificationResult


class AsyncContext:
    """Async context manager test helper."""

    def __init__(self, value: object) -> None:
        self.value = value

    async def __aenter__(self) -> object:
        return self.value

    async def __aexit__(self, *args: object) -> bool:
        return False


def _settings(processing: ProcessingSettings | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        reducto_api_key="reducto-test",
        reducto_base_url="https://reducto.test",
        weaviate_url="http://localhost:8080",
        storage=StorageSettings(),
        chunking=ChunkingSettings(),
        processing=processing or ProcessingSettings(fallback_to_legacy=False),
    )


class TestDocumentState:
    """Tests for DocumentState TypedDict."""

    def test_create_minimal_state(self) -> None:
        state: DocumentState = {"document_id": "test-1", "status": "pending"}
        assert state["document_id"] == "test-1"
        assert state["status"] == "pending"

    def test_create_full_state(self) -> None:
        state: DocumentState = {
            "document_id": "test-1",
            "status": "pending",
            "parsed_content": "# Content",
            "classification_result": {"category": "LPA"},
            "extraction_results": [],
            "summary_text": "",
            "error": None,
            "start_time_ms": 0.0,
            "end_time_ms": 0.0,
            "node_timings": {},
        }
        assert state["error"] is None


class TestNodes:
    """Tests for individual pipeline nodes."""

    @pytest.mark.asyncio
    async def test_parse_node(self) -> None:
        doc_id = uuid.uuid4()
        session = SimpleNamespace(commit=AsyncMock())
        parsed_doc = SimpleNamespace(parsed_path="./data/parsed/test.md")
        parse_service = MagicMock()
        parse_service.parse_document = AsyncMock(return_value=(parsed_doc, "# Parsed", False, 99.0))

        with (
            patch("src.config.settings.get_settings", return_value=_settings()),
            patch(
                "src.db.connection.get_session_factory",
                return_value=lambda: AsyncContext(session),
            ),
            patch("src.services.parse_service.ParseService", return_value=parse_service),
        ):
            result = await parse_node(
                {
                    "document_id": str(doc_id),
                    "file_name": "test.pdf",
                    "status": "pending",
                    "node_timings": {},
                }
            )

        assert result["status"] == "parsed"
        assert result["parsed_content"] == "# Parsed"
        assert "parse" in result["node_timings"]

    @pytest.mark.asyncio
    async def test_classify_node(self) -> None:
        doc_id = uuid.uuid4()
        category_id = uuid.uuid4()
        provider = MagicMock()
        provider.classify = AsyncMock(
            return_value=ClassificationResult(
                category_id=category_id,
                category_name="Other/Unclassified",
                confidence=88,
                reasoning="Bulk classification",
            )
        )

        with (
            patch("src.config.settings.get_settings", return_value=_settings()),
            patch(
                "src.services.processing_providers.get_classification_provider",
                return_value=provider,
            ),
        ):
            result = await classify_node(
                {
                    "document_id": str(doc_id),
                    "file_name": "test.pdf",
                    "original_path": "/tmp/test.pdf",
                    "status": "parsed",
                    "parsed_content": "test content",
                    "categories": [{"id": category_id, "name": "Other/Unclassified"}],
                    "extraction_fields_map": {str(category_id): []},
                    "node_timings": {},
                }
            )

        assert result["status"] == "classified"
        assert result["classification_result"]["category_name"] == "Other/Unclassified"
        assert result["classification_result"]["confidence"] == 88
        assert "classify" in result["node_timings"]

    @pytest.mark.asyncio
    async def test_extract_node_skips_when_no_fields(self) -> None:
        result = await extract_node(
            {
                "document_id": str(uuid.uuid4()),
                "status": "classified",
                "parsed_content": "test",
                "extraction_fields": [],
                "node_timings": {},
            }
        )

        assert result["status"] == "extracted"
        assert result["extraction_results"] == []
        assert "extract" in result["node_timings"]

    @pytest.mark.asyncio
    async def test_extract_node_calls_service(self) -> None:
        doc_id = uuid.uuid4()
        service = MagicMock()
        service.extract_and_judge = AsyncMock(return_value=[{"field_name": "fund_name"}])

        with (
            patch("src.config.settings.get_settings", return_value=_settings()),
            patch("src.services.extraction_service.ExtractionService", return_value=service),
        ):
            result = await extract_node(
                {
                    "document_id": str(doc_id),
                    "status": "classified",
                    "parsed_content": "test",
                    "original_path": "/tmp/test.pdf",
                    "extraction_fields": [
                        {"field_id": str(uuid.uuid4()), "field_name": "fund_name"}
                    ],
                    "node_timings": {},
                }
            )

        assert result["status"] == "extracted"
        assert result["extraction_results"] == [{"field_name": "fund_name"}]

    @pytest.mark.asyncio
    async def test_summarize_node(self) -> None:
        doc_id = uuid.uuid4()
        service = MagicMock()
        service.generate_summary = AsyncMock(return_value={"summary": "Summary for document"})

        with (
            patch("src.config.settings.get_settings", return_value=_settings()),
            patch("src.services.summarize_service.SummaryService", return_value=service),
        ):
            result = await summarize_node(
                {
                    "document_id": str(doc_id),
                    "status": "parsed",
                    "parsed_content": "test",
                    "node_timings": {},
                }
            )

        assert result["status"] == "summarized"
        assert result["summary_text"] == "Summary for document"
        assert "summarize" in result["node_timings"]

    @pytest.mark.asyncio
    async def test_ingest_node(self) -> None:
        doc_id = uuid.uuid4()
        processing = ProcessingSettings(chunking_provider="langchain", fallback_to_legacy=False)
        weaviate = MagicMock()
        service = MagicMock()
        service.ingest_document.return_value = 3
        fake_weaviate_module = types.ModuleType("src.rag.weaviate_client")
        fake_weaviate_module.WeaviateClient = MagicMock(return_value=weaviate)

        with (
            patch("src.config.settings.get_settings", return_value=_settings(processing)),
            patch("src.services.ingest_service.IngestionService", return_value=service),
            patch.dict(sys.modules, {"src.rag.weaviate_client": fake_weaviate_module}),
        ):
            result = await ingest_node(
                {
                    "document_id": str(doc_id),
                    "file_name": "test.pdf",
                    "status": "summarized",
                    "parsed_content": "# Parsed",
                    "node_timings": {},
                }
            )

        assert result["status"] == "ingested"
        assert result["chunks_created"] == 3
        assert "ingest" in result["node_timings"]
        weaviate.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_finalize_node_success(self) -> None:
        result = await finalize_node(
            {"document_id": "doc-1", "status": "ingested", "node_timings": {}}
        )

        assert result["status"] == "completed"
        assert result["end_time_ms"] > 0
        assert "finalize" in result["node_timings"]

    @pytest.mark.asyncio
    async def test_finalize_node_with_error(self) -> None:
        result = await finalize_node(
            {
                "document_id": "doc-1",
                "status": "failed",
                "error": "Something went wrong",
                "node_timings": {},
            }
        )

        assert result["status"] == "failed"


class TestPipeline:
    """Tests for pipeline orchestration helpers."""

    def test_build_pipeline(self) -> None:
        compiled = build_pipeline()
        assert hasattr(compiled, "ainvoke")

    @pytest.mark.asyncio
    async def test_run_pipeline_for_document(self) -> None:
        graph = MagicMock()
        graph.ainvoke = AsyncMock(return_value={"document_id": "doc-1", "status": "completed"})

        result = await run_pipeline_for_document(
            graph,
            {"document_id": "doc-1", "file_name": "test.pdf"},
        )

        assert result["status"] == "completed"
        graph.ainvoke.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_bulk_pipeline_processes_states(self) -> None:
        states = [
            {"document_id": "doc-1", "file_name": "one.pdf"},
            {"document_id": "doc-2", "file_name": "two.pdf"},
        ]
        graph = MagicMock()
        graph.ainvoke = AsyncMock(
            side_effect=[
                {**states[0], "status": "completed"},
                {**states[1], "status": "completed"},
            ]
        )

        with patch("src.bulk.pipeline.build_pipeline", return_value=graph):
            results = await run_bulk_pipeline(states, concurrent_limit=2)

        assert [r["status"] for r in results] == ["completed", "completed"]

    @pytest.mark.asyncio
    async def test_run_bulk_empty(self) -> None:
        results = await run_bulk_pipeline([])
        assert results == []

    def test_build_pipeline_with_custom_checkpointer(self) -> None:
        from langgraph.checkpoint.memory import MemorySaver

        compiled = build_pipeline(checkpointer=MemorySaver())
        assert hasattr(compiled, "ainvoke")


class TestCreateCheckpointer:
    """Tests for the create_checkpointer helper."""

    @pytest.mark.asyncio
    async def test_create_checkpointer_delegates_to_package(self) -> None:
        mock_saver = MagicMock()
        fake_factory = AsyncMock(return_value=mock_saver)
        fake_engine = MagicMock()
        fake_module = types.ModuleType("langgraph_checkpoint_asyncpg")
        fake_module.create_checkpointer = fake_factory

        with patch.dict(sys.modules, {"langgraph_checkpoint_asyncpg": fake_module}):
            result = await create_checkpointer(fake_engine)

        fake_factory.assert_awaited_once_with(fake_engine, auto_setup=True)
        assert result is mock_saver
