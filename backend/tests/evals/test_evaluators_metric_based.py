"""Unit tests for deterministic metric evaluators.

These tests use duck-typed `Run` / `Example` stand-ins so they run without
the LangSmith SDK installed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from evals.evaluators import metric_based as mb


@dataclass
class _FakeRun:
    outputs: dict[str, Any] = field(default_factory=dict)


@dataclass
class _FakeExample:
    outputs: dict[str, Any] = field(default_factory=dict)
    inputs: dict[str, Any] = field(default_factory=dict)


# --- Classification


def test_classification_accuracy_matches_case_insensitively():
    run = _FakeRun(outputs={"category_name": "limited partnership agreement"})
    ex = _FakeExample(outputs={"expected_category": "Limited Partnership Agreement"})
    assert mb.classification_accuracy(run, ex)["score"] == 1.0


def test_classification_accuracy_mismatch():
    run = _FakeRun(outputs={"category_name": "Subscription Agreement"})
    ex = _FakeExample(outputs={"expected_category": "Limited Partnership Agreement"})
    assert mb.classification_accuracy(run, ex)["score"] == 0.0


def test_confidence_in_range_pos():
    run = _FakeRun(outputs={"confidence": 85})
    ex = _FakeExample(outputs={"expected_min_confidence": 80})
    assert mb.classification_confidence_in_range(run, ex)["score"] == 1.0


def test_confidence_in_range_neg():
    run = _FakeRun(outputs={"confidence": 95})
    ex = _FakeExample(outputs={"expected_max_confidence": 60})
    assert mb.classification_confidence_in_range(run, ex)["score"] == 0.0


def test_calibration_ece_perfectly_calibrated():
    # 10 samples in the 80-90 bucket, 9/10 correct, mean conf 85 → |0.85-0.9|=0.05
    runs = [_FakeRun(outputs={"confidence": 85, "category_name": "lpa"}) for _ in range(10)]
    examples = [_FakeExample(outputs={"expected_category": "lpa"}) for _ in range(9)]
    examples.append(_FakeExample(outputs={"expected_category": "other"}))
    result = mb.calibration_error(runs, examples)
    assert result["score"] == pytest.approx(0.05, abs=1e-6)


# --- Extraction


def _extraction_run(field_name: str, value: Any, source_text: str = "") -> _FakeRun:
    return _FakeRun(
        outputs={
            "fields": [
                {"field_name": field_name, "extracted_value": value, "source_text": source_text}
            ]
        }
    )


def test_extraction_exact_match_hits_accepted():
    run = _extraction_run("fund_term", "ten years")
    ex = _FakeExample(
        outputs={
            "field_name": "fund_term",
            "expected_value": "10 years",
            "expected_accepted_values": ["10 years", "ten years"],
        }
    )
    assert mb.extraction_exact_match(run, ex)["score"] == 1.0


def test_extraction_exact_match_misses():
    run = _extraction_run("fund_term", "5 years")
    ex = _FakeExample(
        outputs={"field_name": "fund_term", "expected_value": "10 years"}
    )
    assert mb.extraction_exact_match(run, ex)["score"] == 0.0


def test_extraction_exact_match_respects_expected_empty():
    run = _extraction_run("management_fee_rate", "")
    ex = _FakeExample(
        outputs={"field_name": "management_fee_rate", "expected_empty": True}
    )
    assert mb.extraction_exact_match(run, ex)["score"] == 1.0


def test_extraction_numeric_tolerance_pass():
    run = _extraction_run("fee", "2.01%")
    ex = _FakeExample(
        outputs={
            "field_name": "fee",
            "expected_numeric_value": 2.0,
            "expected_tolerance": 0.05,
        }
    )
    assert mb.extraction_numeric_tolerance(run, ex)["score"] == 1.0


def test_extraction_numeric_tolerance_fail():
    run = _extraction_run("fee", "2.5%")
    ex = _FakeExample(
        outputs={
            "field_name": "fee",
            "expected_numeric_value": 2.0,
            "expected_tolerance": 0.1,
        }
    )
    assert mb.extraction_numeric_tolerance(run, ex)["score"] == 0.0


def test_extraction_source_substring_in_doc():
    run = _extraction_run(
        "fund_name",
        "Horizon Equity Partners IV, L.P.",
        source_text="Horizon Equity Partners IV, L.P. is a Delaware fund.",
    )
    ex = _FakeExample(
        outputs={
            "field_name": "fund_name",
            "expected_source_substring": "Horizon Equity Partners IV",
        },
        inputs={
            "parsed_content": "This is the Horizon Equity Partners IV, L.P. is a Delaware fund. Section 1."
        },
    )
    assert mb.extraction_source_substring(run, ex)["score"] == 1.0


def test_extraction_source_substring_fabricated():
    run = _extraction_run(
        "fund_name",
        "Made Up Capital",
        source_text="Made Up Capital is a fabricated fund.",
    )
    ex = _FakeExample(
        outputs={"field_name": "fund_name"},
        inputs={"parsed_content": "Real document with different content."},
    )
    assert mb.extraction_source_substring(run, ex)["score"] == 0.0


# --- Retrieval


def _retrieval_run(chunk_texts: list[str]) -> _FakeRun:
    return _FakeRun(outputs={"chunks": [{"content": t} for t in chunk_texts]})


def test_recall_at_k_all_found():
    run = _retrieval_run(["management fee is 2.0%", "irrelevant", "Horizon Equity"])
    ex = _FakeExample(
        outputs={"expected_relevant_chunk_substrings": ["management fee", "Horizon Equity"]}
    )
    assert mb.retrieval_recall_at_k(run, ex, k=3)["score"] == 1.0


def test_recall_at_k_partial():
    run = _retrieval_run(["management fee is 2.0%"])
    ex = _FakeExample(
        outputs={"expected_relevant_chunk_substrings": ["management fee", "Horizon Equity"]}
    )
    assert mb.retrieval_recall_at_k(run, ex, k=5)["score"] == 0.5


def test_mrr_hits_at_rank_2():
    run = _retrieval_run(["irrelevant", "management fee is 2.0%"])
    ex = _FakeExample(outputs={"expected_relevant_chunk_substrings": ["management fee"]})
    assert mb.retrieval_mrr(run, ex)["score"] == 0.5


def test_ndcg_at_k_perfect():
    run = _retrieval_run(["management fee", "Horizon"])
    ex = _FakeExample(
        outputs={"expected_relevant_chunk_substrings": ["management fee", "Horizon"]}
    )
    result = mb.retrieval_ndcg_at_k(run, ex, k=10)
    assert result["score"] == 1.0


# --- RAG answer


def test_rag_answer_contains_all_of():
    run = _FakeRun(outputs={"answer": "The management fee is 2.0% per annum."})
    ex = _FakeExample(outputs={"expected_answer_contains": ["2.0%", "per annum"]})
    assert mb.rag_answer_contains(run, ex)["score"] == 1.0


def test_rag_answer_contains_any_of():
    run = _FakeRun(outputs={"answer": "Total: 500 million dollars."})
    ex = _FakeExample(
        outputs={
            "expected_answer_contains": ["500,000,000", "500 million"],
            "expected_answer_match": "any_of",
        }
    )
    assert mb.rag_answer_contains(run, ex)["score"] == 1.0


def test_citation_count_in_range():
    run = _FakeRun(outputs={"citations": [{"id": "1"}, {"id": "2"}]})
    ex = _FakeExample(
        outputs={"expected_min_citations": 1, "expected_max_citations": 3}
    )
    assert mb.rag_citation_count_in_range(run, ex)["score"] == 1.0


# --- Summary


def test_summary_pe_checklist_coverage_full():
    run = _FakeRun(
        outputs={
            "summary": "Horizon Equity Partners IV charges a 2.0% management fee and 20% carry."
        }
    )
    ex = _FakeExample(
        outputs={
            "pe_checklist": {
                "fund_name": "Horizon Equity Partners IV",
                "fee": "2.0%",
                "carry": "20%",
            }
        }
    )
    assert mb.summary_pe_checklist_coverage(run, ex)["score"] == 1.0


def test_summary_pe_checklist_coverage_partial():
    run = _FakeRun(outputs={"summary": "Horizon Equity Partners IV fund."})
    ex = _FakeExample(
        outputs={
            "pe_checklist": {
                "fund_name": "Horizon Equity Partners IV",
                "fee": "2.0%",
            }
        }
    )
    assert mb.summary_pe_checklist_coverage(run, ex)["score"] == 0.5


def test_summary_topic_count_ok():
    run = _FakeRun(outputs={"key_topics": ["a", "b", "c", "d"]})
    ex = _FakeExample(outputs={"expected_min_topics": 3})
    assert mb.summary_topic_count(run, ex)["score"] == 1.0
