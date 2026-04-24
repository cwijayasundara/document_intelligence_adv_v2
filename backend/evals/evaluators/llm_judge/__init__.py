"""LLM-as-judge evaluators — grade subjective qualities deterministic checks can't.

Judges:
    - `faithfulness.py`: summary / RAG answer grounded in source.
    - `relevance.py`:    answer + context relevance.
    - `extraction.py`:   extraction source-fidelity.
    - `sql_intent.py`:   text-to-SQL intent match.
    - `judge_meta.py`:   grades the production Judge node for calibration.
    - `ragas_triad.py`:  optional RAGAS (faithfulness + answer-rel + context-rel).

All judges are async callables with the LangSmith evaluator signature
`(run, example) -> {"key": str, "score": float|None, "comment": str}`.
The judge model is one tier stronger than production, chosen via
`judge_model_name()` in `_base.py`.
"""

from __future__ import annotations

from typing import Any

from ._base import (
    BinaryJudgement,
    FaithfulnessJudgement,
    judge_model_name,
    parse_score,
)
from .extraction import extraction_source_fidelity
from .faithfulness import rag_answer_faithfulness, summary_faithfulness
from .judge_meta import judge_meta_calibration
from .ragas_triad import ragas_triad
from .relevance import rag_answer_relevance, rag_context_relevance
from .sql_intent import sql_intent_match

__all__ = [
    "ALL_EVALUATORS",
    "BinaryJudgement",
    "FaithfulnessJudgement",
    "extraction_source_fidelity",
    "judge_meta_calibration",
    "judge_model_name",
    "parse_score",
    "rag_answer_faithfulness",
    "rag_answer_relevance",
    "rag_context_relevance",
    "ragas_triad",
    "sql_intent_match",
    "summary_faithfulness",
]


ALL_EVALUATORS: dict[str, Any] = {
    "summary_faithfulness": summary_faithfulness,
    "rag_answer_faithfulness": rag_answer_faithfulness,
    "rag_answer_relevance": rag_answer_relevance,
    "rag_context_relevance": rag_context_relevance,
    "extraction_source_fidelity": extraction_source_fidelity,
    "sql_intent_match": sql_intent_match,
    "judge_meta_calibration": judge_meta_calibration,
    "ragas_triad": ragas_triad,
}
