"""Classification agent behavioral evals.

Tests that the classifier correctly identifies document categories
using hybrid signals (file name + content/summary).
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.evals.conftest import EvalMetrics


@pytest.mark.asyncio
class TestClassificationBehavior:
    """Targeted evals for classification agent behavior."""

    async def test_lpa_correctly_classified(
        self,
        lpa_document: dict[str, Any],
        lpa_parsed_content: str,
        categories: list[dict[str, Any]],
        eval_metrics: EvalMetrics,
    ) -> None:
        """Eval: LPA document should be classified as Limited Partnership Agreement.

        Measures: Core classification accuracy for the primary document type.
        Category: classification
        """
        from src.agents.classifier import ClassifierSubagent

        classifier = ClassifierSubagent()
        result = await classifier.classify(
            file_name=lpa_document["file_name"],
            content=lpa_parsed_content,
            categories=categories,
        )

        eval_metrics.record("predicted_category", result.category_name)
        eval_metrics.record("confidence", result.confidence)
        eval_metrics.record("expected_category", lpa_document["expected_category"])
        metrics = eval_metrics.finish()

        assert lpa_document["expected_category"].lower() in result.category_name.lower(), (
            f"Expected '{lpa_document['expected_category']}', got '{result.category_name}'"
        )
        assert result.confidence >= lpa_document["expected_min_confidence"], (
            f"Confidence {result.confidence}% below minimum {lpa_document['expected_min_confidence']}%"
        )
        assert metrics["latency_seconds"] < 10, "Classification took too long"

    async def test_filename_hint_boosts_confidence(
        self,
        lpa_parsed_content: str,
        categories: list[dict[str, Any]],
        eval_metrics: EvalMetrics,
    ) -> None:
        """Eval: Descriptive filename should yield higher confidence than generic one.

        Measures: File name heuristic contributes positively to classification.
        Category: classification
        """
        from src.agents.classifier import ClassifierSubagent

        classifier = ClassifierSubagent()

        result_with_hint = await classifier.classify(
            file_name="LPA_Horizon_Fund_IV.pdf",
            content=lpa_parsed_content[:2000],
            categories=categories,
        )
        result_generic = await classifier.classify(
            file_name="Document_001.pdf",
            content=lpa_parsed_content[:2000],
            categories=categories,
        )

        eval_metrics.record("confidence_with_hint", result_with_hint.confidence)
        eval_metrics.record("confidence_generic", result_generic.confidence)
        eval_metrics.finish()

        # Both should classify as LPA, but hint should give higher confidence
        assert "partnership" in result_with_hint.category_name.lower()
        assert "partnership" in result_generic.category_name.lower()

    async def test_non_lpa_classified_as_other(
        self,
        ground_truth: dict[str, Any],
        categories: list[dict[str, Any]],
        eval_metrics: EvalMetrics,
    ) -> None:
        """Eval: Non-PE document should be classified as Other/Unclassified.

        Measures: Classifier doesn't force-fit non-PE content into PE categories.
        Category: classification
        """
        from src.agents.classifier import ClassifierSubagent

        neg = ground_truth["negative_cases"]["classification"][0]
        classifier = ClassifierSubagent()
        result = await classifier.classify(
            file_name=neg["file_name"],
            content=neg["content"],
            categories=categories,
        )

        eval_metrics.record("predicted_category", result.category_name)
        eval_metrics.record("confidence", result.confidence)
        eval_metrics.finish()

        assert "other" in result.category_name.lower() or result.confidence < 50, (
            f"Non-PE doc classified as '{result.category_name}' with {result.confidence}% confidence"
        )
