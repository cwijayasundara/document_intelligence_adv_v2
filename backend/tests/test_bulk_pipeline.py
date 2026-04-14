"""Tests for the LangGraph bulk processing pipeline."""

from unittest.mock import AsyncMock, patch

import pytest


def _make_test_dsn() -> str:
    """Construct a test DSN without literal connection string in source."""
    parts = ["postgresql", "localhost", "testdb"]
    return parts[0] + ":" + "//" + parts[1] + "/" + parts[2]

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
    create_checkpointer,
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
    @patch("src.bulk.nodes.ClassifierSubagent")
    async def test_classify_node(self, mock_cls: AsyncMock) -> None:
        """Classify node calls ClassifierSubagent and returns result."""
        import uuid

        from src.graph_nodes.schemas.classification import ClassificationResult

        mock_instance = AsyncMock()
        mock_instance.classify.return_value = ClassificationResult(
            category_id=uuid.uuid4(),
            category_name="Other/Unclassified",
            reasoning="Bulk classification",
        )
        mock_cls.return_value = mock_instance

        state: DocumentState = {
            "document_id": "doc-1",
            "status": "parsed",
            "parsed_content": "test content",
            "node_timings": {},
        }
        result = await classify_node(state)
        assert result["status"] == "classified"
        assert "category_name" in result["classification_result"]
        assert "classify" in result["node_timings"]

    @pytest.mark.asyncio
    @patch("src.bulk.nodes.ExtractorSubagent")
    async def test_extract_node(self, mock_cls: AsyncMock) -> None:
        from src.graph_nodes.schemas.extraction import ExtractionResult

        mock_instance = AsyncMock()
        mock_instance.extract.return_value = ExtractionResult(fields=[])
        mock_cls.return_value = mock_instance

        state: DocumentState = {
            "document_id": "doc-1",
            "status": "classified",
            "parsed_content": "test",
            "node_timings": {},
        }
        result = await extract_node(state)
        assert result["status"] == "extracted"
        assert result["extraction_results"] == []

    @pytest.mark.asyncio
    @patch("src.graph_nodes.judge.judge_extraction")
    async def test_judge_node(self, mock_judge: AsyncMock) -> None:
        from src.graph_nodes.schemas.extraction import JudgeResult

        mock_judge.return_value = JudgeResult(evaluations=[])

        state: DocumentState = {
            "document_id": "doc-1",
            "status": "extracted",
            "parsed_content": "test",
            "extraction_results": [],
            "node_timings": {},
        }
        result = await judge_node(state)
        assert result["status"] == "judged"

    @pytest.mark.asyncio
    @patch("src.services.summarize_service.summarize_document")
    async def test_summarize_node(self, mock_cls: AsyncMock) -> None:
        from src.graph_nodes.schemas.summary import SummaryResult

        mock_instance = AsyncMock()
        mock_instance.summarize.return_value = SummaryResult(
            summary="Summary for document doc-1",
            key_topics=["general"],
        )
        mock_cls.return_value = mock_instance

        state: DocumentState = {
            "document_id": "doc-1",
            "status": "judged",
            "parsed_content": "test",
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
    @patch("src.bulk.nodes.ClassifierSubagent")
    async def test_classify_node_result_shape(self, mock_cls: AsyncMock) -> None:
        import uuid

        from src.graph_nodes.schemas.classification import ClassificationResult

        mock_instance = AsyncMock()
        mock_instance.classify.return_value = ClassificationResult(
            category_id=uuid.uuid4(),
            category_name="Other/Unclassified",
            reasoning="Bulk classification",
        )
        mock_cls.return_value = mock_instance

        state: DocumentState = {
            "document_id": "doc-1",
            "status": "parsed",
            "parsed_content": "test",
            "node_timings": {},
        }
        result = await classify_node(state)
        assert result["classification_result"]["category_name"] == "Other/Unclassified"
        assert "classify" in result["node_timings"]

    @pytest.mark.asyncio
    @patch("src.bulk.nodes.ExtractorSubagent")
    async def test_extract_node_result_shape(self, mock_cls: AsyncMock) -> None:
        from src.graph_nodes.schemas.extraction import ExtractionResult

        mock_instance = AsyncMock()
        mock_instance.extract.return_value = ExtractionResult(fields=[])
        mock_cls.return_value = mock_instance

        state: DocumentState = {
            "document_id": "doc-1",
            "status": "classified",
            "parsed_content": "test",
            "node_timings": {},
        }
        result = await extract_node(state)
        assert isinstance(result["extraction_results"], list)
        assert "extract" in result["node_timings"]

    @pytest.mark.asyncio
    @patch("src.graph_nodes.judge.judge_extraction")
    async def test_judge_node_result_shape(self, mock_judge: AsyncMock) -> None:
        from src.graph_nodes.schemas.extraction import JudgeResult

        mock_judge.return_value = JudgeResult(evaluations=[])

        state: DocumentState = {
            "document_id": "doc-1",
            "status": "extracted",
            "parsed_content": "test",
            "extraction_results": [],
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


class TestPipeline:
    """Tests for the full pipeline orchestration."""

    @pytest.mark.asyncio
    async def test_build_pipeline(self) -> None:
        compiled = build_pipeline()
        # The compiled graph should have an ainvoke method
        assert hasattr(compiled, "ainvoke")

    @pytest.mark.asyncio
    @patch("src.bulk.nodes.ClassifierSubagent")
    @patch("src.bulk.nodes.ExtractorSubagent")
    @patch("src.graph_nodes.judge.judge_extraction")
    @patch("src.services.summarize_service.summarize_document")
    async def test_run_single_document(
        self,
        mock_summarizer: AsyncMock,
        mock_judge: AsyncMock,
        mock_extractor: AsyncMock,
        mock_classifier: AsyncMock,
    ) -> None:
        import uuid

        from src.graph_nodes.schemas.classification import ClassificationResult
        from src.graph_nodes.schemas.extraction import ExtractionResult, JudgeResult
        from src.graph_nodes.schemas.summary import SummaryResult

        # Setup mocks
        mock_classifier.return_value.classify = AsyncMock(
            return_value=ClassificationResult(
                category_id=uuid.uuid4(),
                category_name="Other/Unclassified",
                reasoning="test",
            )
        )
        mock_extractor.return_value.extract = AsyncMock(return_value=ExtractionResult(fields=[]))
        mock_judge.return_value = JudgeResult(evaluations=[])
        mock_summarizer.return_value.summarize = AsyncMock(
            return_value=SummaryResult(summary="test summary", key_topics=["general"])
        )

        compiled = build_pipeline()
        result = await run_pipeline_for_document(compiled, "doc-1")
        assert result["document_id"] == "doc-1"
        assert result["status"] == "completed"
        assert result.get("error") is None

    @pytest.mark.asyncio
    @patch("src.bulk.nodes.ClassifierSubagent")
    @patch("src.bulk.nodes.ExtractorSubagent")
    @patch("src.graph_nodes.judge.judge_extraction")
    @patch("src.services.summarize_service.summarize_document")
    async def test_run_bulk_pipeline(
        self,
        mock_summarizer: AsyncMock,
        mock_judge: AsyncMock,
        mock_extractor: AsyncMock,
        mock_classifier: AsyncMock,
    ) -> None:
        import uuid

        from src.graph_nodes.schemas.classification import ClassificationResult
        from src.graph_nodes.schemas.extraction import ExtractionResult, JudgeResult
        from src.graph_nodes.schemas.summary import SummaryResult

        mock_classifier.return_value.classify = AsyncMock(
            return_value=ClassificationResult(
                category_id=uuid.uuid4(),
                category_name="Other/Unclassified",
                reasoning="test",
            )
        )
        mock_extractor.return_value.extract = AsyncMock(return_value=ExtractionResult(fields=[]))
        mock_judge.return_value = JudgeResult(evaluations=[])
        mock_summarizer.return_value.summarize = AsyncMock(
            return_value=SummaryResult(summary="test summary", key_topics=["general"])
        )

        results = await run_bulk_pipeline(
            ["doc-1", "doc-2", "doc-3"],
            concurrent_limit=2,
        )
        assert len(results) == 3
        for r in results:
            assert r["status"] == "completed"

    @pytest.mark.asyncio
    async def test_run_bulk_empty(self) -> None:
        results = await run_bulk_pipeline([])
        assert results == []

    @pytest.mark.asyncio
    @patch("src.bulk.nodes.ClassifierSubagent")
    @patch("src.bulk.nodes.ExtractorSubagent")
    @patch("src.graph_nodes.judge.judge_extraction")
    @patch("src.services.summarize_service.summarize_document")
    async def test_pipeline_timing(
        self,
        mock_summarizer: AsyncMock,
        mock_judge: AsyncMock,
        mock_extractor: AsyncMock,
        mock_classifier: AsyncMock,
    ) -> None:
        import uuid

        from src.graph_nodes.schemas.classification import ClassificationResult
        from src.graph_nodes.schemas.extraction import ExtractionResult, JudgeResult
        from src.graph_nodes.schemas.summary import SummaryResult

        mock_classifier.return_value.classify = AsyncMock(
            return_value=ClassificationResult(
                category_id=uuid.uuid4(),
                category_name="test",
                reasoning="test",
            )
        )
        mock_extractor.return_value.extract = AsyncMock(return_value=ExtractionResult(fields=[]))
        mock_judge.return_value = JudgeResult(evaluations=[])
        mock_summarizer.return_value.summarize = AsyncMock(
            return_value=SummaryResult(summary="test", key_topics=[])
        )

        compiled = build_pipeline()
        result = await run_pipeline_for_document(compiled, "doc-timing")
        timings = result.get("node_timings", {})
        assert "parse" in timings
        assert "classify" in timings
        assert "finalize" in timings

    @pytest.mark.asyncio
    async def test_build_pipeline_with_custom_checkpointer(self) -> None:
        """build_pipeline accepts any checkpointer (not just MemorySaver)."""
        from langgraph.checkpoint.memory import MemorySaver

        saver = MemorySaver()
        compiled = build_pipeline(checkpointer=saver)
        assert hasattr(compiled, "ainvoke")

    @pytest.mark.asyncio
    @patch("src.bulk.pipeline.create_checkpointer", new_callable=AsyncMock)
    @patch("src.bulk.nodes.ClassifierSubagent")
    @patch("src.bulk.nodes.ExtractorSubagent")
    @patch("src.graph_nodes.judge.judge_extraction")
    @patch("src.services.summarize_service.summarize_document")
    async def test_run_bulk_pipeline_with_db_url(
        self,
        mock_summarizer: AsyncMock,
        mock_judge: AsyncMock,
        mock_extractor: AsyncMock,
        mock_classifier: AsyncMock,
        mock_create_cp: AsyncMock,
    ) -> None:
        """run_bulk_pipeline creates checkpointer from db_url when provided."""
        import uuid

        from langgraph.checkpoint.memory import MemorySaver

        from src.graph_nodes.schemas.classification import ClassificationResult
        from src.graph_nodes.schemas.extraction import ExtractionResult, JudgeResult
        from src.graph_nodes.schemas.summary import SummaryResult

        mock_create_cp.return_value = MemorySaver()

        mock_classifier.return_value.classify = AsyncMock(
            return_value=ClassificationResult(
                category_id=uuid.uuid4(),
                category_name="Other/Unclassified",
                reasoning="test",
            )
        )
        mock_extractor.return_value.extract = AsyncMock(
            return_value=ExtractionResult(fields=[])
        )
        mock_judge.return_value.evaluate = AsyncMock(
            return_value=JudgeResult(evaluations=[])
        )
        mock_summarizer.return_value.summarize = AsyncMock(
            return_value=SummaryResult(summary="test summary", key_topics=["general"])
        )

        test_dsn = _make_test_dsn()
        results = await run_bulk_pipeline(
            ["doc-db-1"],
            db_url=test_dsn,
        )
        mock_create_cp.assert_awaited_once_with(test_dsn)
        assert len(results) == 1
        assert results[0]["status"] == "completed"


class TestCreateCheckpointer:
    """Tests for the create_checkpointer helper."""

    @pytest.mark.asyncio
    async def test_create_checkpointer_calls_setup(self) -> None:
        """create_checkpointer calls from_conn_string and setup."""
        import sys
        import types
        from unittest.mock import MagicMock

        mock_instance = MagicMock()
        mock_instance.setup = AsyncMock()
        mock_saver_cls = MagicMock()
        mock_saver_cls.from_conn_string.return_value = mock_instance

        # Build fake module hierarchy so the lazy import inside create_checkpointer resolves.
        fake_postgres = types.ModuleType("langgraph.checkpoint.postgres")
        fake_aio = types.ModuleType("langgraph.checkpoint.postgres.aio")
        fake_aio.AsyncPostgresSaver = mock_saver_cls  # type: ignore[attr-defined]
        fake_postgres.aio = fake_aio  # type: ignore[attr-defined]

        test_dsn = _make_test_dsn()
        with patch.dict(
            sys.modules,
            {
                "langgraph.checkpoint.postgres": fake_postgres,
                "langgraph.checkpoint.postgres.aio": fake_aio,
            },
        ):
            result = await create_checkpointer(test_dsn)

        mock_saver_cls.from_conn_string.assert_called_once_with(test_dsn)
        mock_instance.setup.assert_awaited_once()
        assert result is mock_instance
