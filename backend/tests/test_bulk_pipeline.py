"""Tests for the LangGraph bulk processing pipeline."""

import pytest

from src.bulk.langgraph_stub import CompiledGraph, MemorySaver, StateGraph
from src.bulk.nodes import (
    classify_node,
    extract_node,
    finalize_node,
    ingest_node,
    judge_node,
    parse_node,
    summarize_node,
)
from src.bulk.pipeline import (
    build_pipeline,
    run_bulk_pipeline,
    run_pipeline_for_document,
)
from src.bulk.state import DocumentState


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
            "judge_results": [],
            "summary": "",
            "error": None,
            "start_time_ms": 0.0,
            "end_time_ms": 0.0,
            "node_timings": {},
        }
        assert state["error"] is None


class TestLangGraphStub:
    """Tests for the LangGraph stub implementation."""

    def test_memory_saver(self) -> None:
        saver = MemorySaver()
        saver.save("thread-1", {"key": "value"})
        loaded = saver.load("thread-1")
        assert loaded == {"key": "value"}

    def test_memory_saver_missing(self) -> None:
        saver = MemorySaver()
        assert saver.load("nonexistent") is None

    def test_state_graph_build(self) -> None:
        graph = StateGraph(DocumentState)
        graph.add_node("a", parse_node)
        graph.add_node("b", finalize_node)
        graph.add_edge("a", "b")
        graph.set_entry_point("a")
        graph.set_finish_point("b")
        compiled = graph.compile()
        assert isinstance(compiled, CompiledGraph)

    @pytest.mark.asyncio
    async def test_compiled_graph_invoke(self) -> None:
        graph = StateGraph(DocumentState)
        graph.add_node("a", parse_node)
        graph.add_node("b", finalize_node)
        graph.add_edge("a", "b")
        graph.set_entry_point("a")
        graph.set_finish_point("b")

        compiled = graph.compile()
        result = await compiled.ainvoke(
            {"document_id": "test", "status": "pending", "node_timings": {}},
            config={"configurable": {"thread_id": "test"}},
        )
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_compiled_graph_error_handling(self) -> None:
        async def failing_node(state):
            raise ValueError("Test error")

        graph = StateGraph(DocumentState)
        graph.add_node("fail", failing_node)
        graph.add_node("end", finalize_node)
        graph.add_edge("fail", "end")
        graph.set_entry_point("fail")
        graph.set_finish_point("end")

        compiled = graph.compile()
        result = await compiled.ainvoke(
            {"document_id": "test", "status": "pending"},
        )
        assert "error" in result
        assert "Test error" in result["error"]


class TestNodes:
    """Tests for individual pipeline nodes."""

    @pytest.mark.asyncio
    async def test_parse_node(self) -> None:
        state: DocumentState = {
            "document_id": "doc-1",
            "status": "pending",
            "node_timings": {},
        }
        result = await parse_node(state)
        assert result["status"] == "parsed"
        assert "parse" in result["node_timings"]

    @pytest.mark.asyncio
    async def test_parse_node_with_content(self) -> None:
        state: DocumentState = {
            "document_id": "doc-1",
            "status": "pending",
            "parsed_content": "# Existing content",
            "node_timings": {},
        }
        result = await parse_node(state)
        assert result["parsed_content"] == "# Existing content"

    @pytest.mark.asyncio
    async def test_classify_node(self) -> None:
        state: DocumentState = {
            "document_id": "doc-1",
            "status": "parsed",
            "node_timings": {},
        }
        result = await classify_node(state)
        assert result["status"] == "classified"
        assert "category_name" in result["classification_result"]

    @pytest.mark.asyncio
    async def test_extract_node(self) -> None:
        state: DocumentState = {
            "document_id": "doc-1",
            "status": "classified",
            "node_timings": {},
        }
        result = await extract_node(state)
        assert result["status"] == "extracted"
        assert result["extraction_results"] == []

    @pytest.mark.asyncio
    async def test_judge_node(self) -> None:
        state: DocumentState = {
            "document_id": "doc-1",
            "status": "extracted",
            "node_timings": {},
        }
        result = await judge_node(state)
        assert result["status"] == "judged"

    @pytest.mark.asyncio
    async def test_summarize_node(self) -> None:
        state: DocumentState = {
            "document_id": "doc-1",
            "status": "judged",
            "node_timings": {},
        }
        result = await summarize_node(state)
        assert result["status"] == "summarized"
        assert "doc-1" in result["summary"]

    @pytest.mark.asyncio
    async def test_ingest_node(self) -> None:
        state: DocumentState = {
            "document_id": "doc-1",
            "status": "summarized",
            "node_timings": {},
        }
        result = await ingest_node(state)
        assert result["status"] == "ingested"

    @pytest.mark.asyncio
    async def test_finalize_node_success(self) -> None:
        state: DocumentState = {
            "document_id": "doc-1",
            "status": "ingested",
            "node_timings": {},
        }
        result = await finalize_node(state)
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_finalize_node_with_error(self) -> None:
        state: DocumentState = {
            "document_id": "doc-1",
            "status": "failed",
            "error": "Something went wrong",
            "node_timings": {},
        }
        result = await finalize_node(state)
        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_parse_node_default_content(self) -> None:
        """Test parse node generates content when none exists."""
        state: DocumentState = {
            "document_id": "doc-99",
            "status": "pending",
            "parsed_content": "",
            "node_timings": {},
        }
        result = await parse_node(state)
        assert "doc-99" in result["parsed_content"]

    @pytest.mark.asyncio
    async def test_classify_node_result_shape(self) -> None:
        state: DocumentState = {
            "document_id": "doc-1",
            "status": "parsed",
            "node_timings": {},
        }
        result = await classify_node(state)
        assert result["classification_result"]["category_name"] == "Other/Unclassified"
        assert "classify" in result["node_timings"]

    @pytest.mark.asyncio
    async def test_extract_node_result_shape(self) -> None:
        state: DocumentState = {
            "document_id": "doc-1",
            "status": "classified",
            "node_timings": {},
        }
        result = await extract_node(state)
        assert isinstance(result["extraction_results"], list)
        assert "extract" in result["node_timings"]

    @pytest.mark.asyncio
    async def test_judge_node_result_shape(self) -> None:
        state: DocumentState = {
            "document_id": "doc-1",
            "status": "extracted",
            "node_timings": {},
        }
        result = await judge_node(state)
        assert isinstance(result["judge_results"], list)
        assert "judge" in result["node_timings"]

    @pytest.mark.asyncio
    async def test_ingest_node_result_shape(self) -> None:
        state: DocumentState = {
            "document_id": "doc-1",
            "status": "summarized",
            "node_timings": {},
        }
        result = await ingest_node(state)
        assert "ingest" in result["node_timings"]

    @pytest.mark.asyncio
    async def test_finalize_node_timing(self) -> None:
        state: DocumentState = {
            "document_id": "doc-1",
            "status": "ingested",
            "node_timings": {"parse": 0.01},
        }
        result = await finalize_node(state)
        assert result["end_time_ms"] > 0
        assert "finalize" in result["node_timings"]


class TestNodeErrorHandling:
    """Tests for node error paths."""

    @pytest.mark.asyncio
    async def test_node_error_captured_in_graph(self) -> None:
        """A failing node captures error without raising."""

        async def bad_parse_node(state):
            raise RuntimeError("Parser crashed")

        graph = StateGraph(DocumentState)
        graph.add_node("parse_node", bad_parse_node)
        graph.add_node("finalize_node", finalize_node)
        graph.add_edge("parse_node", "finalize_node")
        graph.set_entry_point("parse_node")
        graph.set_finish_point("finalize_node")

        compiled = graph.compile()
        result = await compiled.ainvoke(
            {"document_id": "err-doc", "status": "pending", "node_timings": {}},
        )
        assert result.get("error") is not None
        assert "Parser crashed" in result["error"]


class TestPipeline:
    """Tests for the full pipeline orchestration."""

    @pytest.mark.asyncio
    async def test_build_pipeline(self) -> None:
        compiled = build_pipeline()
        assert isinstance(compiled, CompiledGraph)

    @pytest.mark.asyncio
    async def test_run_single_document(self) -> None:
        compiled = build_pipeline()
        result = await run_pipeline_for_document(compiled, "doc-1")
        assert result["document_id"] == "doc-1"
        assert result["status"] == "completed"
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_run_single_document_with_content(self) -> None:
        compiled = build_pipeline()
        result = await run_pipeline_for_document(compiled, "doc-2", initial_content="# My document")
        assert result["parsed_content"] == "# My document"
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_run_bulk_pipeline(self) -> None:
        results = await run_bulk_pipeline(
            ["doc-1", "doc-2", "doc-3"],
            concurrent_limit=2,
        )
        assert len(results) == 3
        for r in results:
            assert r["status"] == "completed"

    @pytest.mark.asyncio
    async def test_run_bulk_pipeline_with_checkpointer(self) -> None:
        saver = MemorySaver()
        results = await run_bulk_pipeline(["doc-a"], checkpointer=saver)
        assert len(results) == 1
        # Check checkpointer saved state
        saved = saver.load("doc-a")
        assert saved is not None

    @pytest.mark.asyncio
    async def test_run_bulk_empty(self) -> None:
        results = await run_bulk_pipeline([])
        assert results == []

    @pytest.mark.asyncio
    async def test_pipeline_timing(self) -> None:
        compiled = build_pipeline()
        result = await run_pipeline_for_document(compiled, "doc-timing")
        timings = result.get("node_timings", {})
        assert "parse" in timings
        assert "classify" in timings
        assert "finalize" in timings
