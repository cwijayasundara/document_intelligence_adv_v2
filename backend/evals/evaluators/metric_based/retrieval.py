"""Retrieval metrics — Recall@K, MRR, nDCG."""

from __future__ import annotations

import math
from typing import Any

from ._helpers import HasOutputs, get


def _pred_chunk_texts(run: HasOutputs) -> list[str]:
    """Pull chunk text out of a retrieval prediction.

    Accepts `chunks` with `content`/`text`, or a bare list of strings.
    """
    outputs = run.outputs or {}
    raw = outputs.get("chunks") or outputs.get("retrieved") or []
    texts: list[str] = []
    for chunk in raw:
        if isinstance(chunk, str):
            texts.append(chunk)
        else:
            texts.append(str(get(chunk, "content") or get(chunk, "text") or ""))
    return texts


def _relevance_flags(pred_texts: list[str], required: list[str]) -> list[bool]:
    low_req = [r.lower() for r in required if r]
    return [any(r in t.lower() for r in low_req) for t in pred_texts]


def _first_match_positions(pred_texts: list[str], required: list[str]) -> list[int]:
    """For each required substring, the earliest pred-chunk index that contains it.

    Each required substring counts at most once. This keeps nDCG/recall in [0, 1]
    when multiple retrieved chunks happen to satisfy the same ground-truth signal.
    """
    low_texts = [t.lower() for t in pred_texts]
    positions: list[int] = []
    for r in required:
        r_low = r.lower()
        if not r_low:
            continue
        for i, t in enumerate(low_texts):
            if r_low in t:
                positions.append(i)
                break
    return positions


def retrieval_recall_at_k(run: HasOutputs, example: HasOutputs, k: int = 5) -> dict[str, Any]:
    required = (example.outputs or {}).get("expected_relevant_chunk_substrings") or []
    pred_texts = _pred_chunk_texts(run)[:k]
    found_positions = _first_match_positions(pred_texts, required)
    relevant_found = len(found_positions)
    total_relevant = max(1, len([r for r in required if r]))
    score = relevant_found / total_relevant
    return {
        "key": f"retrieval_recall_at_{k}",
        "score": round(score, 3),
        "comment": f"found={relevant_found} required={len(required)} k={k}",
    }


def retrieval_mrr(run: HasOutputs, example: HasOutputs) -> dict[str, Any]:
    required = (example.outputs or {}).get("expected_relevant_chunk_substrings") or []
    if not required:
        return {"key": "retrieval_mrr", "score": None, "comment": "no required substrings"}
    pred_texts = _pred_chunk_texts(run)
    flags = _relevance_flags(pred_texts, required)
    rr = 0.0
    for idx, ok in enumerate(flags, start=1):
        if ok:
            rr = 1.0 / idx
            break
    return {"key": "retrieval_mrr", "score": round(rr, 4), "comment": f"flags={flags}"}


def retrieval_ndcg_at_k(run: HasOutputs, example: HasOutputs, k: int = 10) -> dict[str, Any]:
    """Binary-relevance nDCG@k.

    A retrieved chunk is relevant iff it contains any required substring.
    IDCG normalises against the relevant chunks actually returned in the top-k,
    which guarantees nDCG in [0, 1] regardless of duplicate matches.
    """
    required = [r for r in ((example.outputs or {}).get("expected_relevant_chunk_substrings") or []) if r]
    if not required:
        return {"key": f"retrieval_ndcg_at_{k}", "score": None, "comment": "no required substrings"}

    pred_texts = _pred_chunk_texts(run)[:k]
    flags = _relevance_flags(pred_texts, required)
    hits = sum(flags)
    dcg = sum(1.0 / math.log2(i + 2) for i, ok in enumerate(flags) if ok)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(hits))
    score = 0.0 if idcg == 0 else dcg / idcg
    return {
        "key": f"retrieval_ndcg_at_{k}",
        "score": round(score, 4),
        "comment": f"dcg={dcg:.3f} idcg={idcg:.3f} hits={hits}/{len(pred_texts)}",
    }
