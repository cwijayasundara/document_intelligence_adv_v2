"""Extraction service: orchestrates extractor -> judge flow."""

from __future__ import annotations

from typing import Any

from src.agents.extractor import ExtractorSubagent
from src.agents.judge import JudgeSubagent

CONFIDENCE_LOW = "low"


class ExtractionService:
    """Orchestrate field extraction and confidence judging."""

    def __init__(
        self,
        extractor: ExtractorSubagent | None = None,
        judge: JudgeSubagent | None = None,
    ) -> None:
        self._extractor = extractor or ExtractorSubagent()
        self._judge = judge or JudgeSubagent()

    async def extract_and_judge(
        self,
        parsed_content: str,
        extraction_fields: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Run extraction then judge, merging confidence scores.

        Args:
            parsed_content: Document markdown content.
            extraction_fields: Field definitions with field_id, field_name, etc.

        Returns:
            List of result dicts with merged confidence data.
        """
        extraction_result = await self._extractor.extract(parsed_content, extraction_fields)

        judge_result = await self._judge.evaluate(extraction_result.fields, parsed_content)

        eval_map = {e.field_name: e for e in judge_result.evaluations}

        results = []
        for i, field_def in enumerate(extraction_fields):
            extracted = extraction_result.fields[i] if i < len(extraction_result.fields) else None
            evaluation = eval_map.get(field_def["field_name"])

            confidence = evaluation.confidence if evaluation else "medium"
            reasoning = evaluation.reasoning if evaluation else ""
            requires_review = confidence == CONFIDENCE_LOW

            results.append(
                {
                    "field_id": field_def["field_id"],
                    "field_name": field_def["field_name"],
                    "display_name": field_def.get("display_name", ""),
                    "extracted_value": extracted.extracted_value if extracted else "",
                    "source_text": extracted.source_text if extracted else "",
                    "confidence": confidence,
                    "confidence_reasoning": reasoning,
                    "requires_review": requires_review,
                }
            )

        return results
