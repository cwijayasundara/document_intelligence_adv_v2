"""Adapt `backend/evals` Example/RunRecord shapes -> Foundry row dicts."""

from __future__ import annotations

from typing import Any


def _join_chunks(chunks: Any) -> str:
    if not chunks:
        return ""
    if isinstance(chunks, str):
        return chunks
    parts: list[str] = []
    for c in chunks:
        if isinstance(c, dict):
            parts.append(c.get("content") or c.get("text") or c.get("chunk_text") or "")
        else:
            parts.append(str(c))
    return "\n\n".join(p for p in parts if p)


def to_safety_row(
    example_inputs: dict[str, Any],
    outputs: dict[str, Any],
    *,
    query_field: str = "query",
) -> dict[str, Any]:
    """Build a {query, response, context} row from a stage's prediction.

    `outputs` is a runner's `_predict()` return — works for rag (`answer` +
    `chunks`), summary (`summary`), and agentic_rag (`answer` + nothing else).
    `context` is recovered from retrieved chunks if present, else from
    `example_inputs.context`.
    """
    response = (
        outputs.get("answer")
        or outputs.get("summary")
        or outputs.get("response")
        or ""
    )
    context = _join_chunks(outputs.get("chunks") or example_inputs.get("context"))
    return {
        "query": example_inputs.get(query_field) or "",
        "response": response,
        "context": context,
    }


def to_doc_retrieval_row(
    example_outputs: dict[str, Any],
    run_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Convert RAG-style chunks + expected substrings into qrels + scored hits.

    Foundry's `document_retrieval` evaluator wants
        retrieval_ground_truth: [{document_id, query_relevance_label}]
        retrieved_documents:    [{document_id, relevance_score}]

    The current dataset uses `expected_relevant_chunk_substrings`. We label a
    retrieved chunk as relevant (level 4) if any expected substring appears
    in its text, else 0. The label range is [0, 4].
    """
    expected = example_outputs.get("expected_relevant_chunk_substrings") or []
    chunks = run_outputs.get("chunks") or []
    retrieved: list[dict[str, Any]] = []
    qrels: list[dict[str, Any]] = []
    for i, c in enumerate(chunks):
        if isinstance(c, dict):
            text = c.get("content") or c.get("text") or c.get("chunk_text") or ""
            score = c.get("score")
        else:
            text = str(c)
            score = None
        relevance_score = float(score) if isinstance(score, (int, float)) else float(len(chunks) - i)
        retrieved.append({"document_id": str(i), "relevance_score": relevance_score})
        label = 4 if any(s.lower() in text.lower() for s in expected) else 0
        qrels.append({"document_id": str(i), "query_relevance_label": label})
    return {"retrieval_ground_truth": qrels, "retrieved_documents": retrieved}
