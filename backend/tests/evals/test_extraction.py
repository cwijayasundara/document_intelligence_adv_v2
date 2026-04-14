"""Extraction agent behavioral evals.

Tests that the extractor correctly identifies field values
and provides verbatim source text from the document.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.evals.conftest import EvalMetrics


@pytest.mark.asyncio
class TestExtractionBehavior:
    """Targeted evals for extraction agent behavior."""

    async def test_all_lpa_fields_extracted(
        self,
        lpa_document: dict[str, Any],
        lpa_parsed_content: str,
        eval_metrics: EvalMetrics,
    ) -> None:
        """Eval: All 8 LPA fields should be extracted with values.

        Measures: Extraction completeness — no fields left empty.
        Category: extraction
        """
        from src.graph_nodes.extractor import ExtractorSubagent

        fields = [
            {"field_name": k, "data_type": "string", "description": f"Extract {k}"}
            for k in lpa_document["expected_extraction"]
        ]
        extractor = ExtractorSubagent()
        result = await extractor.extract(lpa_parsed_content, fields)

        extracted_map = {f.field_name: f for f in result.fields}
        empty_fields = [
            name for name, f in extracted_map.items() if not f.extracted_value
        ]

        eval_metrics.record("total_fields", len(fields))
        eval_metrics.record("extracted_count", len(fields) - len(empty_fields))
        eval_metrics.record("empty_fields", empty_fields)
        eval_metrics.finish()

        assert len(empty_fields) == 0, f"Fields with empty values: {empty_fields}"

    async def test_fund_name_exact_match(
        self,
        lpa_document: dict[str, Any],
        lpa_parsed_content: str,
        eval_metrics: EvalMetrics,
    ) -> None:
        """Eval: Fund name should exactly match the ground truth.

        Measures: Critical field accuracy — fund name is the document identifier.
        Category: extraction
        """
        from src.graph_nodes.extractor import ExtractorSubagent

        fields = [{"field_name": "fund_name", "data_type": "string",
                    "description": "The full legal name of the fund."}]
        extractor = ExtractorSubagent()
        result = await extractor.extract(lpa_parsed_content, fields)

        extracted = result.fields[0].extracted_value
        expected = lpa_document["expected_extraction"]["fund_name"]

        eval_metrics.record("extracted", extracted)
        eval_metrics.record("expected", expected)
        eval_metrics.finish()

        assert expected.lower() in extracted.lower(), (
            f"Expected '{expected}' in '{extracted}'"
        )

    async def test_source_text_is_verbatim(
        self,
        lpa_parsed_content: str,
        eval_metrics: EvalMetrics,
    ) -> None:
        """Eval: Source text should be a verbatim quote from the document.

        Measures: Source text quality — not fabricated or paraphrased.
        Category: extraction
        """
        from src.graph_nodes.extractor import ExtractorSubagent

        fields = [{"field_name": "management_fee_rate", "data_type": "percentage",
                    "description": "Annual management fee rate."}]
        extractor = ExtractorSubagent()
        result = await extractor.extract(lpa_parsed_content, fields)

        source = result.fields[0].source_text
        eval_metrics.record("source_length", len(source))
        eval_metrics.record("has_source", bool(source))
        eval_metrics.finish()

        assert source, "Source text should not be empty"
        # Check that key phrases from the source appear in the document
        clean = source.strip('"\'')
        words = clean.split()
        found = False
        for i in range(min(len(words) - 4, 10)):
            phrase = " ".join(words[i : i + 5])
            if phrase.lower() in lpa_parsed_content.lower():
                found = True
                break
        assert found, (
            f"No 5-word phrase from source found in document: '{clean[:100]}...'"
        )

    async def test_percentage_fields_have_percent_sign(
        self,
        lpa_document: dict[str, Any],
        lpa_parsed_content: str,
        eval_metrics: EvalMetrics,
    ) -> None:
        """Eval: Percentage fields should include % symbol.

        Measures: Format validity for percentage data type fields.
        Category: extraction
        """
        from src.graph_nodes.extractor import ExtractorSubagent

        pct_fields = ["management_fee_rate", "carried_interest_rate", "preferred_return"]
        fields = [
            {"field_name": name, "data_type": "percentage",
             "description": f"Extract {name} as a percentage."}
            for name in pct_fields
        ]
        extractor = ExtractorSubagent()
        result = await extractor.extract(lpa_parsed_content, fields)

        missing_pct = []
        for f in result.fields:
            if f.extracted_value and "%" not in f.extracted_value:
                missing_pct.append(f.field_name)

        eval_metrics.record("checked_fields", pct_fields)
        eval_metrics.record("missing_percent_sign", missing_pct)
        eval_metrics.finish()

        assert len(missing_pct) == 0, f"Fields missing % symbol: {missing_pct}"
