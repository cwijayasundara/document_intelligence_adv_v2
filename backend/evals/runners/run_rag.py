"""Basic RAG runner — retrieval + answer generation + RAGAS triad."""

from __future__ import annotations

from typing import Any

from ._base import Example, run_experiment as _run_experiment


async def _predict(example: Example) -> dict[str, Any]:
    from src.config.settings import get_settings
    from src.rag.weaviate_client import WeaviateClient
    from src.services.rag_service import RAGService

    inputs = example.inputs
    query = inputs.get("query") or ""
    doc_id = inputs.get("doc_id")

    settings = get_settings()
    client = WeaviateClient(url=settings.weaviate_url)
    client.connect()
    service = RAGService(client)
    try:
        response = await service.query(
            query=query,
            scope="single_document" if doc_id else "all",
            scope_id=doc_id,
            search_mode="hybrid",
            top_k=10,
        )
    finally:
        try:
            client.disconnect()
        except Exception:  # noqa: BLE001
            pass

    citations = response.get("citations") or []
    return {
        "answer": response.get("answer") or "",
        # Evaluators look up `content` or `text` on each chunk.
        "chunks": [
            {
                "content": c.get("chunk_text", ""),
                "text": c.get("chunk_text", ""),
                "score": c.get("relevance_score"),
                "document_id": c.get("document_id"),
                "chunk_index": c.get("chunk_index"),
                "section": c.get("section"),
            }
            for c in citations
        ],
        "citations": citations,
        "citation_count": response.get("chunks_retrieved", len(citations)),
    }


def _evaluators() -> list[tuple[str, Any]]:
    import os

    from evals.evaluators.metric_based import (
        rag_answer_contains,
        rag_citation_count_in_range,
        retrieval_mrr,
        retrieval_ndcg_at_k,
        retrieval_recall_at_k,
    )

    evs: list[tuple[str, Any]] = [
        ("retrieval_recall_at_5", lambda r, e: retrieval_recall_at_k(r, e, k=5)),
        ("retrieval_mrr", retrieval_mrr),
        ("retrieval_ndcg_at_10", lambda r, e: retrieval_ndcg_at_k(r, e, k=10)),
        ("rag_answer_contains", rag_answer_contains),
        ("rag_citation_count_in_range", rag_citation_count_in_range),
    ]
    if os.environ.get("OPENAI_API_KEY"):
        from evals.evaluators.llm_judge import (
            rag_answer_faithfulness,
            rag_answer_relevance,
            rag_context_relevance,
            ragas_triad,
        )

        evs.extend(
            [
                ("rag_answer_faithfulness", rag_answer_faithfulness),
                ("rag_answer_relevance", rag_answer_relevance),
                ("rag_context_relevance", rag_context_relevance),
                ("ragas_triad", ragas_triad),
            ]
        )
    return evs


async def run_experiment_wrapper(
    subset: int | None = None,
    tags: list[str] | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    return await _run_experiment(
        stage="rag",
        dataset_file="rag_golden.jsonl",
        predict=_predict,
        evaluators=_evaluators(),
        subset=subset,
        tags=tags,
        model=model,
    )


run_experiment = run_experiment_wrapper  # alias for CLI discovery
