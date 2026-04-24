"""Rubric runner — score predictions against YAML-defined multi-criterion rubrics.

A rubric is a YAML file under `backend/evals/rubrics/<name>.yaml`. Each
criterion has an `id`, `description`, `weight`, and optional `anchors`.
The runner asks a judge LLM to score each criterion on the rubric's scale
(e.g. 1..5), returns per-criterion + composite scores, and preserves the
full rationale for auditing.

Usage:
    from evals.evaluators.rubric import run_rubric

    result = await run_rubric(
        rubric_name="extraction",
        context={"document": "...", "field_name": "fund_name"},
        prediction={"extracted_value": "Horizon Equity Partners IV, L.P."},
    )
    # → {"key": "rubric_extraction", "score": 0.86, "raw_score": 4.3, "criteria": {...}}
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

RUBRIC_DIR = Path(__file__).resolve().parent.parent / "rubrics"


@dataclass(frozen=True)
class Rubric:
    name: str
    description: str
    scale: tuple[int, int]
    criteria: list[dict[str, Any]]
    judge_model_hint: str = "strong"

    @property
    def total_weight(self) -> float:
        return sum(float(c.get("weight", 0.0)) for c in self.criteria) or 1.0


def load_rubric(name: str) -> Rubric:
    path = RUBRIC_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"rubric not found: {path}")
    data = yaml.safe_load(path.read_text()) or {}
    scale = data.get("scale") or [1, 5]
    return Rubric(
        name=data.get("name", name),
        description=data.get("description", ""),
        scale=(int(scale[0]), int(scale[1])),
        criteria=list(data.get("criteria", [])),
        judge_model_hint=data.get("judge_model_hint", "strong"),
    )


class CriterionScore(BaseModel):
    id: str
    score: float = Field(..., description="Score within the rubric's scale.")
    reasoning: str = Field(..., description="One-sentence justification.")


class RubricVerdict(BaseModel):
    scores: list[CriterionScore]
    overall_comment: str = ""


def _format_criterion(c: dict[str, Any]) -> str:
    parts = [
        f"- id: {c['id']}",
        f"  weight: {c.get('weight', 0)}",
        f"  description: {c.get('description', '')}",
    ]
    anchors = c.get("anchors") or {}
    if anchors:
        parts.append("  anchors:")
        for k in sorted(anchors.keys()):
            parts.append(f"    {k}: {anchors[k]}")
    scoring = c.get("scoring")
    if scoring:
        parts.append(f"  scoring: {scoring}")
    return "\n".join(parts)


def _system_prompt(rubric: Rubric) -> str:
    lo, hi = rubric.scale
    criteria_block = "\n".join(_format_criterion(c) for c in rubric.criteria)
    return (
        f"You grade model outputs against the '{rubric.name}' rubric. For each\n"
        f"criterion below, return a score in the inclusive range [{lo}, {hi}]\n"
        f"and a one-sentence justification. Use the anchors / scoring guidance\n"
        f"where provided. Return `scores` in the same order as the criteria\n"
        f"listed, plus an optional `overall_comment`.\n\n"
        f"RUBRIC: {rubric.description}\n\n"
        f"CRITERIA:\n{criteria_block}"
    )


def _format_context(payload: Any) -> str:
    """Render the context/prediction payload in a readable form for the judge."""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        parts = []
        for key, value in payload.items():
            if isinstance(value, str) and len(value) > 6000:
                value = value[:6000] + "\n…[truncated]"
            parts.append(f"{key}: {value}")
        return "\n".join(parts)
    return str(payload)


async def run_rubric(
    rubric_name: str,
    context: dict[str, Any],
    prediction: dict[str, Any],
    model: str | None = None,
) -> dict[str, Any]:
    """Score `prediction` against `rubric_name` given `context`.

    Returns
        {"key": f"rubric_{name}", "score": <normalised 0..1>, "raw_score": <on scale>,
         "criteria": {...}, "comment": "..."}.
    """
    rubric = load_rubric(rubric_name)

    from src.graph_nodes.llm import get_llm

    if model is None:
        from evals.evaluators.llm_judge import judge_model_name

        model = judge_model_name()

    llm = get_llm(model=model, temperature=0).with_structured_output(RubricVerdict)

    system = _system_prompt(rubric)
    user = (
        f"CONTEXT:\n{_format_context(context)}\n\n---\nPREDICTION:\n{_format_context(prediction)}"
    )

    from langchain_core.messages import HumanMessage, SystemMessage

    verdict: RubricVerdict = await llm.ainvoke(
        [SystemMessage(content=system), HumanMessage(content=user)]
    )  # type: ignore[assignment]

    return _aggregate(rubric, verdict)


def _aggregate(rubric: Rubric, verdict: RubricVerdict) -> dict[str, Any]:
    lo, hi = rubric.scale
    by_id = {s.id: s for s in verdict.scores}
    criteria_scores: dict[str, dict[str, Any]] = {}
    weighted_sum = 0.0

    for c in rubric.criteria:
        cid = c["id"]
        weight = float(c.get("weight", 0.0))
        got = by_id.get(cid)
        raw = float(got.score) if got else float(lo)
        raw = max(float(lo), min(float(hi), raw))
        normalised = (raw - lo) / max(1e-9, (hi - lo))
        weighted_sum += weight * normalised
        criteria_scores[cid] = {
            "score": raw,
            "weight": weight,
            "reasoning": got.reasoning if got else "missing from judge response",
        }

    composite = weighted_sum / rubric.total_weight
    raw_composite = (
        sum(cs["score"] * cs["weight"] for cs in criteria_scores.values()) / rubric.total_weight
    )
    return {
        "key": f"rubric_{rubric.name}",
        "score": round(composite, 4),
        "raw_score": round(raw_composite, 4),
        "criteria": criteria_scores,
        "comment": verdict.overall_comment
        or "; ".join(f"{k}={v['score']}" for k, v in criteria_scores.items()),
    }


def make_rubric_evaluator(rubric_name: str, context_keys: list[str] | None = None):
    """Build a LangSmith-style `(run, example) -> dict` evaluator for a rubric.

    `context_keys` controls which `example.inputs` keys are passed as judge
    context (e.g. `["parsed_content", "field_name"]` for extraction).
    """

    async def _scorer(run: Any, example: Any) -> dict[str, Any]:
        inputs = (getattr(example, "inputs", None) or {}) if example is not None else {}
        context_payload = {k: inputs.get(k) for k in context_keys} if context_keys else dict(inputs)
        prediction = getattr(run, "outputs", None) or {}
        return await run_rubric(rubric_name, context_payload, prediction)

    return _scorer
