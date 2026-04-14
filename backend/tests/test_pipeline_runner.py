"""Tests for PipelineRunner (start, resume, get_status).

All LangGraph graph calls and database access are mocked so no real
LLM APIs or databases are touched.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.pipeline.runner import PipelineRunner


def _make_mock_graph(
    invoke_return: dict[str, Any] | None = None,
    state_snapshot: Any | None = None,
) -> MagicMock:
    """Create a mock compiled LangGraph graph."""
    graph = MagicMock()
    graph.ainvoke = AsyncMock(
        return_value=invoke_return
        or {
            "document_id": "test-id",
            "status": "completed",
            "node_statuses": {},
        }
    )
    graph.get_state = MagicMock(return_value=state_snapshot)
    return graph


class TestPipelineRunnerStart:
    """Tests for PipelineRunner.start."""

    @pytest.mark.asyncio
    async def test_start_invokes_graph_with_initial_state(self) -> None:
        graph = _make_mock_graph()
        runner = PipelineRunner(compiled_graph=graph)
        doc_id = uuid.uuid4()

        with patch.object(runner, "_save_thread_id", new_callable=AsyncMock):
            result = await runner.start(
                document_id=doc_id,
                file_name="LPA_Fund.pdf",
                original_path="/uploads/LPA_Fund.pdf",
                categories=[{"id": str(uuid.uuid4()), "name": "LPA"}],
                extraction_fields_map={},
            )

        graph.ainvoke.assert_called_once()
        call_args = graph.ainvoke.call_args
        initial_state = call_args[0][0]
        assert initial_state["document_id"] == str(doc_id)
        assert initial_state["file_name"] == "LPA_Fund.pdf"
        assert initial_state["status"] == "processing"
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_start_passes_thread_id_in_config(self) -> None:
        graph = _make_mock_graph()
        runner = PipelineRunner(compiled_graph=graph)
        doc_id = uuid.uuid4()

        with patch.object(runner, "_save_thread_id", new_callable=AsyncMock):
            await runner.start(
                document_id=doc_id,
                file_name="doc.pdf",
                original_path="/uploads/doc.pdf",
                categories=[],
                extraction_fields_map={},
            )

        call_kwargs = graph.ainvoke.call_args[1]
        assert call_kwargs["config"]["configurable"]["thread_id"] == str(doc_id)

    @pytest.mark.asyncio
    async def test_start_saves_thread_id(self) -> None:
        graph = _make_mock_graph()
        runner = PipelineRunner(compiled_graph=graph)
        doc_id = uuid.uuid4()

        with patch.object(runner, "_save_thread_id", new_callable=AsyncMock) as mock_save:
            await runner.start(
                document_id=doc_id,
                file_name="doc.pdf",
                original_path="/uploads/doc.pdf",
                categories=[],
                extraction_fields_map={},
            )

        mock_save.assert_called_once_with(doc_id, str(doc_id))


class TestPipelineRunnerResume:
    """Tests for PipelineRunner.resume."""

    @pytest.mark.asyncio
    async def test_resume_invokes_with_command(self) -> None:
        graph = _make_mock_graph()
        runner = PipelineRunner(compiled_graph=graph)
        doc_id = uuid.uuid4()

        with patch.object(
            runner, "_get_thread_id", new_callable=AsyncMock, return_value=str(doc_id)
        ):
            result = await runner.resume(
                document_id=doc_id,
                resume_data={"approved": True, "edits": {}},
            )

        graph.ainvoke.assert_called_once()
        call_args = graph.ainvoke.call_args[0][0]
        # Should be a Command with resume data
        assert hasattr(call_args, "resume")
        assert call_args.resume == {"approved": True, "edits": {}}
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_resume_defaults_to_approved_true(self) -> None:
        graph = _make_mock_graph()
        runner = PipelineRunner(compiled_graph=graph)
        doc_id = uuid.uuid4()

        with patch.object(
            runner, "_get_thread_id", new_callable=AsyncMock, return_value=str(doc_id)
        ):
            await runner.resume(document_id=doc_id, resume_data=None)

        call_args = graph.ainvoke.call_args[0][0]
        assert call_args.resume == {"approved": True}

    @pytest.mark.asyncio
    async def test_resume_uses_doc_id_when_no_thread_id(self) -> None:
        graph = _make_mock_graph()
        runner = PipelineRunner(compiled_graph=graph)
        doc_id = uuid.uuid4()

        with patch.object(runner, "_get_thread_id", new_callable=AsyncMock, return_value=None):
            await runner.resume(document_id=doc_id)

        call_kwargs = graph.ainvoke.call_args[1]
        assert call_kwargs["config"]["configurable"]["thread_id"] == str(doc_id)


class TestPipelineRunnerGetStatus:
    """Tests for PipelineRunner.get_status."""

    @pytest.mark.asyncio
    async def test_get_status_returns_node_statuses(self) -> None:
        snapshot = MagicMock()
        snapshot.values = {
            "status": "paused",
            "node_statuses": {"parse": {"status": "completed"}},
            "node_timings": {"parse": 1.23},
        }
        snapshot.next = ("summarize",)

        graph = _make_mock_graph(state_snapshot=snapshot)
        runner = PipelineRunner(compiled_graph=graph)
        doc_id = uuid.uuid4()

        with patch.object(
            runner, "_get_thread_id", new_callable=AsyncMock, return_value=str(doc_id)
        ):
            status = await runner.get_status(doc_id)

        assert status is not None
        assert status["status"] == "paused"
        assert status["node_statuses"] == {"parse": {"status": "completed"}}
        assert status["node_timings"] == {"parse": 1.23}
        assert status["next_nodes"] == ["summarize"]

    @pytest.mark.asyncio
    async def test_get_status_returns_none_when_no_state(self) -> None:
        snapshot = MagicMock()
        snapshot.values = {}

        graph = _make_mock_graph(state_snapshot=snapshot)
        runner = PipelineRunner(compiled_graph=graph)
        doc_id = uuid.uuid4()

        with patch.object(
            runner, "_get_thread_id", new_callable=AsyncMock, return_value=str(doc_id)
        ):
            status = await runner.get_status(doc_id)

        assert status is None

    @pytest.mark.asyncio
    async def test_get_status_returns_none_when_snapshot_none(self) -> None:
        graph = _make_mock_graph(state_snapshot=None)
        runner = PipelineRunner(compiled_graph=graph)
        doc_id = uuid.uuid4()

        with patch.object(
            runner, "_get_thread_id", new_callable=AsyncMock, return_value=str(doc_id)
        ):
            status = await runner.get_status(doc_id)

        assert status is None

    @pytest.mark.asyncio
    async def test_get_status_empty_next_nodes(self) -> None:
        snapshot = MagicMock()
        snapshot.values = {
            "status": "completed",
            "node_statuses": {},
            "node_timings": {},
        }
        snapshot.next = None

        graph = _make_mock_graph(state_snapshot=snapshot)
        runner = PipelineRunner(compiled_graph=graph)
        doc_id = uuid.uuid4()

        with patch.object(
            runner, "_get_thread_id", new_callable=AsyncMock, return_value=str(doc_id)
        ):
            status = await runner.get_status(doc_id)

        assert status is not None
        assert status["next_nodes"] == []
