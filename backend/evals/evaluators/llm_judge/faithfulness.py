"""Faithfulness judges — summary and RAG answer grounded-in-source checks."""

from __future__ import annotations

from typing import Any

from ._base import FaithfulnessJudgement, HasOutputs, get, structured_call

SYSTEM = """You are a strict faithfulness judge. Given a SOURCE document and a
PREDICTION, decide whether every factual claim in the PREDICTION is supported
by the SOURCE. Do not reward plausible-sounding claims; only direct support
counts.

Return:
  - `faithful`: true only if every claim is supported.
  - `score`: fraction of claims that are supported (0..1).
  - `unsupported_claims`: list the problematic claims verbatim (empty if faithful).
  - `reasoning`: one sentence summary.
""".strip()


async def summary_faithfulness(run: HasOutputs, example: HasOutputs) -> dict[str, Any]:
    summary = get(run.outputs, "summary") or ""
    inputs = get(example, "inputs", {}) or {}
    source = inputs.get("parsed_content") or inputs.get("inline_content") or ""
    if not summary or not source:
        return {
            "key": "summary_faithfulness",
            "score": None,
            "comment": "missing summary or source",
        }

    user = f"SOURCE:\n{source[:12000]}\n\n---\nPREDICTION (summary):\n{summary}"
    judged: FaithfulnessJudgement = await structured_call(SYSTEM, user, FaithfulnessJudgement)  # type: ignore[assignment]
    return {
        "key": "summary_faithfulness",
        "score": round(judged.score, 3),
        "comment": (
            f"faithful={judged.faithful} "
            f"unsupported={judged.unsupported_claims!r} — {judged.reasoning}"
        ),
    }


async def rag_answer_faithfulness(run: HasOutputs, _example: HasOutputs) -> dict[str, Any]:
    """Is the RAG answer grounded in the retrieved chunks it used?"""
    answer = get(run.outputs, "answer") or get(run.outputs, "text") or ""
    chunks = get(run.outputs, "chunks") or get(run.outputs, "citations") or []
    context = "\n\n---\n\n".join(str(get(c, "content") or get(c, "text") or c) for c in chunks)
    if not answer or not context:
        return {
            "key": "rag_answer_faithfulness",
            "score": None,
            "comment": "missing answer/context",
        }
    user = f"SOURCE (retrieved chunks):\n{context[:12000]}\n\n---\nPREDICTION (answer):\n{answer}"
    judged: FaithfulnessJudgement = await structured_call(SYSTEM, user, FaithfulnessJudgement)  # type: ignore[assignment]
    return {
        "key": "rag_answer_faithfulness",
        "score": round(judged.score, 3),
        "comment": f"faithful={judged.faithful} — {judged.reasoning}",
    }
