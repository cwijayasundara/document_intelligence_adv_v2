"""Shared judge plumbing — model selection, structured-call helper, schemas."""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Protocol

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class HasOutputs(Protocol):
    outputs: dict[str, Any] | None


def judge_model_name() -> str:
    """Pick the judge model — one tier stronger than production by default."""
    explicit = os.environ.get("EVAL_JUDGE_MODEL")
    if explicit:
        return explicit
    prod = os.environ.get("OPENAI_MODEL", "gpt-5.2")
    upgrades = {
        "gpt-5.2": "gpt-5.3",
        "gpt-5.2-mini": "gpt-5.3",
        "gpt-5.1": "gpt-5.2",
        "gpt-5.1-mini": "gpt-5.2",
    }
    return upgrades.get(prod, prod)


def get_judge_llm():
    """Materialise the judge LLM — kept lazy so importing doesn't need LangChain."""
    from src.graph_nodes.llm import get_llm

    return get_llm(model=judge_model_name(), temperature=0)


async def structured_call(system: str, user: str, schema: type[BaseModel]) -> BaseModel:
    """Invoke the judge LLM with structured output."""
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = get_judge_llm().with_structured_output(schema)
    return await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=user)])


def get(obj: Any, key: str, default: Any = None) -> Any:
    """Look up a key on either a dict or an attribute, with a default."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def parse_score(text: str) -> float | None:
    """Pull a leading float from judge free-text (fallback for non-structured calls)."""
    match = _NUMBER_RE.search(text or "")
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


# --- Structured schemas shared across judges.


class BinaryJudgement(BaseModel):
    passed: bool = Field(..., description="True when the criterion is met.")
    score: float = Field(
        ..., ge=0.0, le=1.0, description="Soft score — useful when the judge can grade degree."
    )
    reasoning: str = Field(..., description="One-sentence justification.")


class FaithfulnessJudgement(BaseModel):
    faithful: bool = Field(
        ..., description="True when every claim in the prediction is supported by the source."
    )
    score: float = Field(..., ge=0.0, le=1.0)
    unsupported_claims: list[str] = Field(
        default_factory=list,
        description="Claims from the prediction that are not supported by the source.",
    )
    reasoning: str = Field(...)


class AnswerRelevanceJudgement(BaseModel):
    on_topic: bool
    score: float = Field(..., ge=0.0, le=1.0)
    reasoning: str


class ContextRelevanceJudgement(BaseModel):
    per_chunk_scores: list[float] = Field(default_factory=list)
    mean_score: float = Field(..., ge=0.0, le=1.0)
    reasoning: str


class JudgeMetaJudgement(BaseModel):
    calibrated: bool = Field(
        ..., description="True when high-confidence predictions are correct and low are not."
    )
    score: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
