"""Relevance judges — answer-relevance and context-relevance."""

from __future__ import annotations

from typing import Any

from ._base import (
    AnswerRelevanceJudgement,
    ContextRelevanceJudgement,
    HasOutputs,
    get,
    structured_call,
)

ANSWER_RELEVANCE_SYSTEM = """You are an answer-relevance judge. Given a
QUESTION and an ANSWER, decide whether the ANSWER actually addresses the
QUESTION (without concern for factual accuracy — that is graded separately).

Return `score` in [0,1] where:
  - 1.0: answer fully addresses the question.
  - 0.5: answer is partially on-topic.
  - 0.0: answer ignores the question or answers a different one.
""".strip()


CONTEXT_RELEVANCE_SYSTEM = """You grade each retrieved CHUNK on how relevant
it is to the QUESTION. Return `per_chunk_scores` with one float per chunk (1.0
= directly relevant; 0.0 = unrelated), plus `mean_score`.
""".strip()


async def rag_answer_relevance(run: HasOutputs, example: HasOutputs) -> dict[str, Any]:
    answer = get(run.outputs, "answer") or get(run.outputs, "text") or ""
    query = get(example, "inputs", {}).get("query") or ""
    if not answer or not query:
        return {"key": "rag_answer_relevance", "score": None, "comment": "missing answer/query"}
    user = f"QUESTION:\n{query}\n\n---\nANSWER:\n{answer}"
    judged: AnswerRelevanceJudgement = await structured_call(
        ANSWER_RELEVANCE_SYSTEM, user, AnswerRelevanceJudgement
    )  # type: ignore[assignment]
    return {
        "key": "rag_answer_relevance",
        "score": round(judged.score, 3),
        "comment": judged.reasoning,
    }


async def rag_context_relevance(run: HasOutputs, example: HasOutputs) -> dict[str, Any]:
    query = get(example, "inputs", {}).get("query") or ""
    chunks = get(run.outputs, "chunks") or []
    if not query or not chunks:
        return {"key": "rag_context_relevance", "score": None, "comment": "missing query/chunks"}
    numbered = "\n".join(
        f"[{i}] {str(get(c, 'content') or get(c, 'text') or c)[:1500]}"
        for i, c in enumerate(chunks)
    )
    user = f"QUESTION:\n{query}\n\n---\nCHUNKS:\n{numbered}"
    judged: ContextRelevanceJudgement = await structured_call(
        CONTEXT_RELEVANCE_SYSTEM, user, ContextRelevanceJudgement
    )  # type: ignore[assignment]
    return {
        "key": "rag_context_relevance",
        "score": round(judged.mean_score, 3),
        "comment": f"per_chunk={judged.per_chunk_scores} — {judged.reasoning}",
    }
