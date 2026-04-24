"""RAGAS triad — faithfulness + answer-relevance + context-precision.

Migrated to the post-migration ragas API: `ragas.metrics.collections` classes
with explicit LLM + embedding injection via `llm_factory` / `OpenAIEmbeddings`.
No more `ragas.evaluate()` / Dataset round-trip.

When ragas is not installed, or any of its calls raise, the evaluator returns
`score=None` so the rest of the run keeps going.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
from typing import Any

from ._base import HasOutputs, get

logger = logging.getLogger(__name__)

_client = None  # cached AsyncOpenAI client (process-scoped)
_triad = None   # cached (Faithfulness, AnswerRelevancy, ContextPrecision) instances


def _get_triad() -> tuple[Any, Any, Any] | None:
    """Lazily build and cache the three metric instances."""
    global _client, _triad
    if _triad is not None:
        return _triad

    try:
        from openai import AsyncOpenAI
        from ragas.embeddings import OpenAIEmbeddings as RagasEmbeddings
        from ragas.llms import llm_factory
        from ragas.metrics.collections import (
            AnswerRelevancy,
            ContextPrecision,
            Faithfulness,
        )

        from src.config.settings import get_settings
    except ImportError as exc:
        logger.info("ragas not available: %s", exc)
        return None

    settings = get_settings()
    judge_model = settings.ragas_judge_model
    emb_model = settings.ragas_embedding_model

    try:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
        llm = llm_factory(judge_model, client=_client)
        embeddings = RagasEmbeddings(client=_client, model=emb_model)
        _triad = (
            Faithfulness(llm=llm),
            AnswerRelevancy(llm=llm, embeddings=embeddings),
            ContextPrecision(llm=llm),
        )
    except Exception as exc:  # noqa: BLE001 — degrade gracefully, don't poison the run.
        logger.warning("ragas_triad init failed: %s", exc)
        return None
    return _triad


async def ragas_triad(run: HasOutputs, example: HasOutputs) -> dict[str, Any]:
    """Run RAGAS triad in one batch. Composite mean → `score`; per-metric → `comment`."""
    triad = _get_triad()
    if triad is None:
        return {"key": "ragas_triad", "score": None, "comment": "ragas unavailable"}
    faithfulness, answer_relevancy, context_precision = triad

    query = (get(example, "inputs", {}) or {}).get("query") or ""
    answer = get(run.outputs, "answer") or get(run.outputs, "text") or ""
    chunks = get(run.outputs, "chunks") or []
    contexts = [str(get(c, "content") or get(c, "text") or c) for c in chunks]
    reference = (example.outputs or {}).get("reference_answer") or ""

    if not answer or not contexts:
        return {
            "key": "ragas_triad",
            "score": None,
            "comment": f"insufficient input (answer={bool(answer)} contexts={len(contexts)})",
        }

    async def _safe(coro, name: str) -> float | None:
        try:
            result = await coro
            val = getattr(result, "value", result)
            f = float(val) if isinstance(val, (int, float)) else None
            return f if f is not None and math.isfinite(f) else None
        except Exception as exc:  # noqa: BLE001 — one metric shouldn't kill the triad.
            logger.warning("ragas %s failed: %s", name, exc)
            return None

    raw_f, raw_ar, raw_cp = await asyncio.gather(
        _safe(faithfulness.ascore(query, answer, contexts), "faithfulness"),
        _safe(answer_relevancy.ascore(query, answer), "answer_relevancy"),
        _safe(
            context_precision.ascore(query, reference or answer, contexts),
            "context_precision",
        ),
    )
    scores = {
        "faithfulness": raw_f,
        "answer_relevancy": raw_ar,
        "context_precision": raw_cp,
    }
    finite = {k: v for k, v in scores.items() if isinstance(v, float)}
    if not finite:
        return {
            "key": "ragas_triad",
            "score": None,
            "comment": f"no finite metrics: {scores}",
        }

    composite = sum(finite.values()) / len(finite)
    return {
        "key": "ragas_triad",
        "score": round(composite, 3),
        "comment": json.dumps({k: round(v, 3) for k, v in finite.items()}),
    }
