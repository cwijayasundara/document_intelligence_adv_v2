"""RAG retriever behavioral evals.

Tests retrieval relevance, answer groundedness,
and multi-turn conversation support.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.evals.conftest import EvalMetrics


def _connect_weaviate():
    """Try to connect to Weaviate, skip if unavailable."""
    try:
        from src.config.settings import get_settings
        from src.rag.weaviate_client import WeaviateClient
    except (ImportError, ModuleNotFoundError) as exc:
        pytest.skip(f"Weaviate/reranker not installed: {exc}")

    settings = get_settings()
    client = WeaviateClient(url=settings.weaviate_url)
    try:
        client.connect()
        if not client.is_connected:
            pytest.skip("Weaviate not connected")
        return client
    except Exception as exc:
        pytest.skip(f"Weaviate unavailable: {exc}")


@pytest.mark.asyncio
class TestRAGBehavior:
    """Targeted evals for RAG retriever behavior."""

    async def test_answer_contains_expected_content(
        self,
        lpa_document: dict[str, Any],
        eval_metrics: EvalMetrics,
    ) -> None:
        """Eval: RAG answer for management fee query should contain '2.0%'.

        Measures: Answer accuracy — the core fact must be present.
        Category: rag, groundedness
        """
        try:
            from src.services.rag_service import RAGService
        except (ImportError, ModuleNotFoundError) as exc:
            pytest.skip(f"RAG dependencies not installed: {exc}")

        weaviate = _connect_weaviate()
        try:
            service = RAGService(weaviate_client=weaviate)
            rag_query = lpa_document["rag_queries"][0]
            result = await service.query(
                query=rag_query["query"],
                scope="all",
                search_mode="hybrid",
                top_k=5,
            )

            if result["chunks_retrieved"] == 0:
                pytest.skip("No chunks ingested — ingest documents first")

            answer_lower = result["answer"].lower()
            expected = rag_query["expected_answer_contains"]
            found = [e for e in expected if e.lower() in answer_lower]

            eval_metrics.record("query", rag_query["query"])
            eval_metrics.record("answer_length", len(result["answer"]))
            eval_metrics.record("citations", result["chunks_retrieved"])
            eval_metrics.record("expected_terms_found", found)
            eval_metrics.finish()

            assert len(found) > 0, (
                f"Answer missing expected terms {expected}. Answer: {result['answer'][:200]}"
            )
            assert result["chunks_retrieved"] >= rag_query["expected_min_citations"]
        finally:
            weaviate.disconnect()

    async def test_retrieval_returns_relevant_chunks(
        self,
        eval_metrics: EvalMetrics,
    ) -> None:
        """Eval: Searching for 'management fee' should retrieve fee-related chunks.

        Measures: Retrieval relevance — top chunks should contain the query topic.
        Category: rag, retrieval_relevance
        """
        weaviate = _connect_weaviate()
        try:
            results = weaviate.search(query="management fee", top_k=3)

            if not results:
                pytest.skip("No chunks in Weaviate — ingest documents first")

            eval_metrics.record("chunks_returned", len(results))
            relevant = [
                r for r in results
                if "fee" in r.chunk_text.lower() or "management" in r.chunk_text.lower()
            ]
            eval_metrics.record("relevant_chunks", len(relevant))
            eval_metrics.finish()

            assert len(relevant) > 0, "No relevant chunks in top results"
        finally:
            weaviate.disconnect()

    async def test_multiturn_uses_conversation_context(
        self,
        eval_metrics: EvalMetrics,
    ) -> None:
        """Eval: Follow-up question should use prior conversation context.

        Measures: Multi-turn memory — agent remembers previous Q&A.
        Category: rag, memory
        """
        from src.agents.memory import get_short_term_memory

        memory = get_short_term_memory()
        session_id = "eval_multiturn_test"

        memory.add_human_message(session_id, "What is the management fee?")
        memory.add_ai_message(session_id, "The management fee is 2.0% per annum.")

        history = memory.get_conversation_summary(session_id)

        eval_metrics.record("history_length", len(history))
        eval_metrics.finish()

        assert "management fee" in history.lower()
        assert "2.0%" in history

        memory.delete_session(session_id)
