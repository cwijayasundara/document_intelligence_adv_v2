"""RAG answer metrics — content containment + citation count bounds."""

from __future__ import annotations

from typing import Any

from ._helpers import HasOutputs, extract_numeric, get, norm_loose


def rag_answer_contains(run: HasOutputs, example: HasOutputs) -> dict[str, Any]:
    """Checks `expected_answer_contains` against the generated answer.

    `expected_answer_match`:
      - "all_of" (default) — every substring must appear.
      - "any_of"           — at least one must appear.
    """
    expected = example.outputs or {}
    must_contain = expected.get("expected_answer_contains") or []
    match_mode = expected.get("expected_answer_match", "all_of")
    answer = norm_loose(get(run.outputs, "answer") or get(run.outputs, "text") or "")

    if not must_contain:
        return {"key": "rag_answer_contains", "score": None, "comment": "no constraints"}

    normalised = [norm_loose(s) for s in must_contain]
    hits = [s for s in normalised if s and s in answer]
    if match_mode == "any_of":
        ok = len(hits) > 0
    else:
        ok = len(hits) == len(normalised)

    return {
        "key": "rag_answer_contains",
        "score": 1.0 if ok else round(len(hits) / max(1, len(normalised)), 3),
        "comment": f"mode={match_mode} hits={hits} required={normalised}",
    }


def rag_citation_count_in_range(run: HasOutputs, example: HasOutputs) -> dict[str, Any]:
    expected = example.outputs or {}
    lo = expected.get("expected_min_citations")
    hi = expected.get("expected_max_citations")
    count = extract_numeric(get(run.outputs, "citation_count"))
    if count is None:
        citations = get(run.outputs, "citations") or []
        count = float(len(citations))

    ok_lo = lo is None or count >= float(lo)
    ok_hi = hi is None or count <= float(hi)
    ok = ok_lo and ok_hi
    return {
        "key": "rag_citation_count_in_range",
        "score": 1.0 if ok else 0.0,
        "comment": f"count={count} min={lo} max={hi}",
    }
