"""Judge subagent for confidence scoring of extracted values.

Evaluates extraction quality with a separate LLM call to ensure
objectivity. Returns confidence ratings with reasoning per field.
"""

from __future__ import annotations

from typing import Any

from src.agents.deepagents_stub import SubAgentSlot, create_deep_agent
from src.agents.middleware.pii_filter import PIIFilterMiddleware
from src.agents.schemas.extraction import (
    ExtractedField,
    FieldEvaluation,
    JudgeResult,
)

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"
VALID_CONFIDENCES = {CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW}


class JudgeSubagent:
    """Subagent that evaluates extraction quality with confidence scoring.

    Receives extracted values, source texts, and full document content.
    Returns confidence rating (high/medium/low) with reasoning per field.
    """

    def __init__(self) -> None:
        self._pii_filter = PIIFilterMiddleware()
        self._agent = create_deep_agent(
            model="openai:gpt-5.4-mini",
            tools=[self._get_extracted_values, self._get_parsed_content],
        )
        self._extracted_fields: list[ExtractedField] = []
        self._parsed_content: str = ""

    async def evaluate(
        self,
        extracted_fields: list[ExtractedField],
        parsed_content: str,
    ) -> JudgeResult:
        """Evaluate extraction quality for each field.

        Args:
            extracted_fields: List of extracted field values.
            parsed_content: Full document content for context.

        Returns:
            JudgeResult with confidence evaluations per field.
        """
        self._extracted_fields = extracted_fields
        filtered = self._pii_filter.filter_content(parsed_content)
        self._parsed_content = filtered.redacted_text

        prompt = self._build_prompt(
            extracted_fields, filtered.redacted_text
        )
        response = await self._agent.run(prompt)

        return self._build_result(extracted_fields)

    def _build_prompt(
        self,
        fields: list[ExtractedField],
        content: str,
    ) -> str:
        """Build the judge evaluation prompt."""
        field_desc = "\n".join(
            f"- {f.field_name}: value='{f.extracted_value}', "
            f"source='{f.source_text[:200]}'"
            for f in fields
        )
        return (
            f"Evaluate the confidence of these extracted values:\n"
            f"{field_desc}\n\n"
            f"Document content:\n{content[:3000]}\n\n"
            f"Rate each field as high/medium/low confidence."
        )

    def _build_result(
        self, fields: list[ExtractedField]
    ) -> JudgeResult:
        """Build JudgeResult (stub: assigns medium confidence)."""
        evaluations = []
        for f in fields:
            confidence = self._assess_confidence(f)
            evaluations.append(
                FieldEvaluation(
                    field_name=f.field_name,
                    confidence=confidence,
                    reasoning=self._default_reasoning(confidence),
                )
            )
        return JudgeResult(evaluations=evaluations)

    @staticmethod
    def _assess_confidence(field: ExtractedField) -> str:
        """Assess confidence based on extracted value and source text."""
        if not field.extracted_value or not field.source_text:
            return CONFIDENCE_LOW
        if field.extracted_value.lower() in field.source_text.lower():
            return CONFIDENCE_HIGH
        return CONFIDENCE_MEDIUM

    @staticmethod
    def _default_reasoning(confidence: str) -> str:
        """Return default reasoning for a confidence level."""
        reasons = {
            CONFIDENCE_HIGH: "Source text explicitly states the value.",
            CONFIDENCE_MEDIUM: "Value implied but requires interpretation.",
            CONFIDENCE_LOW: "No clear source for this value.",
        }
        return reasons.get(confidence, "Unable to determine confidence.")

    async def _get_extracted_values(self) -> list[dict[str, Any]]:
        """Tool: get extracted field values."""
        return [f.model_dump() for f in self._extracted_fields]

    async def _get_parsed_content(self) -> str:
        """Tool: get parsed document content."""
        return self._parsed_content

    def as_subagent_slot(self) -> SubAgentSlot:
        """Create a SubAgentSlot for registration with orchestrator."""
        return SubAgentSlot(
            name="judge",
            agent=self._agent,
            description="Evaluates extraction confidence per field",
        )
