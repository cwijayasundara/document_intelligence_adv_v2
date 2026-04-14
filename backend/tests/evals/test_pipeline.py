"""End-to-end pipeline behavioral evals.

Tests the full document processing pipeline efficiency
and judge calibration accuracy.
"""

from __future__ import annotations

import pytest

from tests.evals.conftest import EvalMetrics


@pytest.mark.asyncio
class TestPipelineBehavior:
    """Targeted evals for end-to-end pipeline behavior."""

    async def test_judge_confidence_calibration(
        self,
        lpa_parsed_content: str,
        eval_metrics: EvalMetrics,
    ) -> None:
        """Eval: Judge should rate correct extractions as high confidence.

        Measures: Confidence calibration — high confidence should mean correct.
        Category: pipeline, judge
        """
        from src.agents.extractor import ExtractorSubagent
        from src.agents.judge import judge_extraction

        fields = [
            {"field_name": "fund_name", "data_type": "string",
             "description": "Full legal name of the fund.",
             "required": True, "examples": "Horizon Equity Partners IV, L.P."},
        ]
        extractor = ExtractorSubagent()
        extraction = await extractor.extract(lpa_parsed_content, fields)

        judge_result = await judge_extraction(
            extraction.fields, lpa_parsed_content, field_metadata=fields
        )

        eval_metrics.record("extraction", extraction.fields[0].extracted_value)
        eval_metrics.record("source_text_present", bool(extraction.fields[0].source_text))

        if judge_result.evaluations:
            confidence = judge_result.evaluations[0].confidence
            eval_metrics.record("judge_confidence", confidence)
            eval_metrics.finish()
            # Correct extraction + source text should get high confidence
            assert confidence == "high", (
                f"Expected 'high' confidence for correct extraction, got '{confidence}'"
            )
        else:
            eval_metrics.finish()
            pytest.fail("Judge returned no evaluations")

    async def test_extraction_service_caches_results(
        self,
        lpa_parsed_content: str,
        eval_metrics: EvalMetrics,
    ) -> None:
        """Eval: Second extraction should return cached results (no LLM call).

        Measures: Caching efficiency — avoids redundant LLM calls.
        Category: pipeline, efficiency
        """
        import time
        import uuid

        from src.config.settings import get_settings
        from src.services.extraction_service import ExtractionService

        settings = get_settings()
        service = ExtractionService(extraction_dir=settings.storage.extraction_dir)
        doc_id = uuid.uuid4()

        fields = [
            {"field_name": "fund_name", "field_id": doc_id, "data_type": "string",
             "description": "Fund name", "required": True},
        ]

        # First call — LLM
        start1 = time.time()
        result1 = await service.extract_and_judge(
            doc_id=doc_id, parsed_content=lpa_parsed_content, extraction_fields=fields
        )
        time1 = time.time() - start1

        # Second call — should be cached
        start2 = time.time()
        result2 = await service.extract_and_judge(
            doc_id=doc_id, parsed_content=lpa_parsed_content, extraction_fields=fields
        )
        time2 = time.time() - start2

        eval_metrics.record("first_call_seconds", round(time1, 2))
        eval_metrics.record("second_call_seconds", round(time2, 2))
        eval_metrics.record("speedup", round(time1 / max(time2, 0.001), 1))
        eval_metrics.finish()

        # Cached call should be significantly faster
        assert time2 < time1 * 0.5, (
            f"Cache not effective: first={time1:.2f}s, second={time2:.2f}s"
        )
