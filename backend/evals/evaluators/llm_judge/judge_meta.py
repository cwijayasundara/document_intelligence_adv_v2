"""Judge-meta evaluator — grades the production Judge node's calibration."""

from __future__ import annotations

from typing import Any

from ._base import HasOutputs, JudgeMetaJudgement, get, structured_call

SYSTEM = """You review how well a production JUDGE rated an extraction. You
are given:
  - The FIELD.
  - The EXTRACTED_VALUE and the GOLD_VALUE (if known).
  - The production JUDGE's confidence (high / medium / low) and its REASONING.

Decide whether the judge's confidence is appropriate:
  - high + value matches gold       → well-calibrated (score 1.0).
  - high + value differs from gold  → over-confident (score 0.0).
  - low  + value matches gold       → under-confident (score 0.3).
  - low  + value differs from gold  → well-calibrated (score 1.0).
  - medium + value matches gold     → modestly under-confident (score 0.7).
  - medium + value differs from gold→ modestly over-confident (score 0.4).

Return `calibrated`, `score`, and one-sentence `reasoning`.
""".strip()


async def judge_meta_calibration(run: HasOutputs, example: HasOutputs) -> dict[str, Any]:
    field_name = get(example.outputs, "field_name") or get(example, "inputs", {}).get("field_name")
    extraction = get(run.outputs, "extraction") or {}
    evaluations = get(run.outputs, "evaluations") or []

    predicted_value: Any = None
    for f in extraction.get("fields") or []:
        if get(f, "field_name") == field_name:
            predicted_value = get(f, "extracted_value")
            break

    judge_verdict: dict[str, Any] | None = None
    for ev in evaluations:
        if get(ev, "field_name") == field_name:
            judge_verdict = (
                ev
                if isinstance(ev, dict)
                else {"confidence": get(ev, "confidence"), "reasoning": get(ev, "reasoning")}
            )
            break
    if judge_verdict is None:
        return {"key": "judge_meta_calibration", "score": None, "comment": "no judge verdict"}

    gold = (example.outputs or {}).get("expected_value")
    user = (
        f"FIELD: {field_name}\nEXTRACTED_VALUE: {predicted_value!r}\n"
        f"GOLD_VALUE: {gold!r}\n"
        f"JUDGE.confidence: {judge_verdict.get('confidence')}\n"
        f"JUDGE.reasoning: {judge_verdict.get('reasoning')}"
    )
    judged: JudgeMetaJudgement = await structured_call(SYSTEM, user, JudgeMetaJudgement)  # type: ignore[assignment]
    return {
        "key": "judge_meta_calibration",
        "score": round(judged.score, 3),
        "comment": f"calibrated={judged.calibrated} — {judged.reasoning}",
    }
