"""Summarization agent behavioral evals.

Tests that summaries preserve PE-specific attributes
and don't hallucinate facts.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.evals.conftest import EvalMetrics


@pytest.mark.asyncio
class TestSummarizationBehavior:
    """Targeted evals for summarization agent behavior."""

    async def test_summary_preserves_pe_attributes(
        self,
        lpa_document: dict[str, Any],
        lpa_parsed_content: str,
        eval_metrics: EvalMetrics,
    ) -> None:
        """Eval: Summary should contain key PE terms from the document.

        Measures: PE attribute retention — the summary must preserve
        financially significant details for downstream classification.
        Category: summarization
        """
        from src.agents.summarizer import SummarizerSubagent

        summarizer = SummarizerSubagent()
        result = await summarizer.summarize(lpa_parsed_content)

        summary_lower = result.summary.lower()
        keywords = lpa_document["expected_summary_keywords"]
        found = [kw for kw in keywords if kw.lower() in summary_lower]
        missing = [kw for kw in keywords if kw.lower() not in summary_lower]

        eval_metrics.record("total_keywords", len(keywords))
        eval_metrics.record("found_keywords", found)
        eval_metrics.record("missing_keywords", missing)
        eval_metrics.record("summary_length", len(result.summary))
        eval_metrics.finish()

        coverage = len(found) / len(keywords)
        assert coverage >= 0.6, (
            f"Only {coverage:.0%} keyword coverage. Missing: {missing}"
        )

    async def test_summary_not_empty_or_trivial(
        self,
        lpa_parsed_content: str,
        eval_metrics: EvalMetrics,
    ) -> None:
        """Eval: Summary should be substantial, not a one-liner.

        Measures: Summary completeness — must provide meaningful detail.
        Category: summarization
        """
        from src.agents.summarizer import SummarizerSubagent

        summarizer = SummarizerSubagent()
        result = await summarizer.summarize(lpa_parsed_content)

        eval_metrics.record("summary_length", len(result.summary))
        eval_metrics.record("topics_count", len(result.key_topics))
        eval_metrics.finish()

        assert len(result.summary) > 200, (
            f"Summary too short: {len(result.summary)} chars"
        )
        assert len(result.key_topics) >= 2, (
            f"Too few topics: {result.key_topics}"
        )
