"""Text-to-SQL intent-match judge."""

from __future__ import annotations

from typing import Any

from ._base import BinaryJudgement, HasOutputs, get, structured_call

SYSTEM = """You are a PE-finance analyst reviewing a generated SQL query.
Given the USER_QUESTION and the GENERATED_SQL, decide whether the SQL —
if it executes correctly — would answer the USER_QUESTION as a reasonable
analyst would interpret it.

Ignore stylistic preferences; judge intent only. Return `passed`, `score`
(in [0,1]), and `reasoning`.
""".strip()


async def sql_intent_match(run: HasOutputs, example: HasOutputs) -> dict[str, Any]:
    sql = get(run.outputs, "sql") or ""
    question = get(example, "inputs", {}).get("question") or ""
    if not sql or not question:
        return {"key": "sql_intent_match", "score": None, "comment": "missing sql/question"}
    user = f"USER_QUESTION:\n{question}\n\n---\nGENERATED_SQL:\n{sql}"
    judged: BinaryJudgement = await structured_call(SYSTEM, user, BinaryJudgement)  # type: ignore[assignment]
    return {
        "key": "sql_intent_match",
        "score": round(judged.score, 3),
        "comment": f"passed={judged.passed} — {judged.reasoning}",
    }
