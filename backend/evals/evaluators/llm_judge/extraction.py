"""Extraction source-fidelity judge.

Goes beyond substring match: an LLM decides whether the predicted
`source_text` is actually the best passage supporting the extracted value.
"""

from __future__ import annotations

from typing import Any

from ._base import BinaryJudgement, HasOutputs, get, structured_call

SYSTEM = """You judge whether a claimed SOURCE_TEXT is the actual passage in
the DOCUMENT from which a VALUE was extracted for a given FIELD.

Pass only if all three are true:
  (a) SOURCE_TEXT appears (substring, whitespace-tolerant) in DOCUMENT.
  (b) VALUE is supported by SOURCE_TEXT.
  (c) SOURCE_TEXT is the BEST passage in the document for this field — not a
      loosely-related sentence.

Return `passed`, a score in [0,1] (1.0 pass, 0.5 partial, 0.0 fail), and a
one-sentence `reasoning`.
""".strip()


async def extraction_source_fidelity(run: HasOutputs, example: HasOutputs) -> dict[str, Any]:
    outputs = run.outputs or {}
    field_name = get(example.outputs, "field_name") or get(example, "inputs", {}).get("field_name")
    pred = None
    for f in outputs.get("fields") or []:
        if get(f, "field_name") == field_name:
            pred = f
            break
    if pred is None:
        return {"key": "extraction_source_fidelity", "score": 0.0, "comment": "no prediction"}

    value = get(pred, "extracted_value")
    source_text = get(pred, "source_text")
    inputs = get(example, "inputs", {}) or {}
    document = inputs.get("parsed_content") or inputs.get("inline_content") or ""
    if not document or not source_text or value in (None, ""):
        return {
            "key": "extraction_source_fidelity",
            "score": None,
            "comment": "nothing to judge",
        }

    user = (
        f"FIELD: {field_name}\nVALUE: {value}\nSOURCE_TEXT: {source_text}\n\n"
        f"DOCUMENT:\n{document[:12000]}"
    )
    judged: BinaryJudgement = await structured_call(SYSTEM, user, BinaryJudgement)  # type: ignore[assignment]
    return {
        "key": "extraction_source_fidelity",
        "score": round(judged.score, 3),
        "comment": f"passed={judged.passed} — {judged.reasoning}",
    }
