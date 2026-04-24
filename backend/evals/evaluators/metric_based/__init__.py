"""Deterministic, metric-based evaluators — cheap and reproducible.

Every evaluator follows the LangSmith evaluator shape:

    def evaluator(run, example) -> {"key": str, "score": float | bool, "comment": str}

`run.outputs` holds the production prediction; `example.outputs` holds the
golden reference. A thin duck-typed contract is used so the same evaluators
can be unit-tested without a real LangSmith SDK — each argument just needs
an `.outputs` dict and (for example) a `.metadata` / `.inputs` dict.

Split by concern to stay under the 300-line file limit:
    - `classification.py` — accuracy, confidence-in-range, ECE.
    - `extraction.py`     — exact match, numeric tolerance, source substring.
    - `retrieval.py`      — Recall@K, MRR, nDCG for labelled chunks.
    - `rag_answer.py`     — answer-contains + citation-count bounds.
    - `summary.py`        — PE-checklist coverage, topic-count.
"""

from __future__ import annotations

from typing import Any

from .classification import (
    calibration_error,
    classification_accuracy,
    classification_confidence_in_range,
)
from .extraction import (
    extraction_exact_match,
    extraction_numeric_tolerance,
    extraction_source_substring,
)
from .rag_answer import rag_answer_contains, rag_citation_count_in_range
from .retrieval import retrieval_mrr, retrieval_ndcg_at_k, retrieval_recall_at_k
from .summary import summary_pe_checklist_coverage, summary_topic_count

__all__ = [
    "ALL_EVALUATORS",
    "calibration_error",
    "classification_accuracy",
    "classification_confidence_in_range",
    "extraction_exact_match",
    "extraction_numeric_tolerance",
    "extraction_source_substring",
    "rag_answer_contains",
    "rag_citation_count_in_range",
    "retrieval_mrr",
    "retrieval_ndcg_at_k",
    "retrieval_recall_at_k",
    "summary_pe_checklist_coverage",
    "summary_topic_count",
]


ALL_EVALUATORS: dict[str, Any] = {
    "classification_accuracy": classification_accuracy,
    "classification_confidence_in_range": classification_confidence_in_range,
    "calibration_ece": calibration_error,
    "extraction_exact_match": extraction_exact_match,
    "extraction_numeric_tolerance": extraction_numeric_tolerance,
    "extraction_source_substring": extraction_source_substring,
    "retrieval_recall_at_5": lambda r, e: retrieval_recall_at_k(r, e, k=5),
    "retrieval_mrr": retrieval_mrr,
    "retrieval_ndcg_at_10": lambda r, e: retrieval_ndcg_at_k(r, e, k=10),
    "rag_answer_contains": rag_answer_contains,
    "rag_citation_count_in_range": rag_citation_count_in_range,
    "summary_pe_checklist_coverage": summary_pe_checklist_coverage,
    "summary_topic_count": summary_topic_count,
}
