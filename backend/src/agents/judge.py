"""Judge subagent for confidence scoring of extracted values.

Evaluates extraction quality with a separate LLM call to ensure
objectivity. Returns confidence ratings with reasoning per field.
"""

from __future__ import annotations

from typing import Any

from deepagents import SubAgent, create_deep_agent

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
    Uses a separate agent instance for objectivity.
    """

    def __init__(self) -> None:
        self._pii_filter = PIIFilterMiddleware()
        self._agent = create_deep_agent(
            model="openai:gpt-5.4-mini",
            tools=[self._get_extracted_values, self._get_parsed_content],
            system_prompt=(
                "You are an extraction quality judge for a PE document intelligence system. "
                "Given a set of extracted field values and the original document content, "
                "evaluate the confidence of each extraction as high, medium, or low. "
                "Provide reasoning for each assessment."
            ),
            response_format=JudgeResult,
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

        if not extracted_fields:
            return JudgeResult(evaluations=[])

        prompt = self._build_prompt(extracted_fields, filtered.redacted_text)
        result = await self._agent.ainvoke(prompt)

        return self._parse_result(result, extracted_fields)

    def _build_prompt(
        self,
        fields: list[ExtractedField],
        content: str,
    ) -> str:
        """Build the judge evaluation prompt."""
        field_desc = "\n".join(
            f"- {f.field_name}: value='{f.extracted_value}', source='{f.source_text[:200]}'"
            for f in fields
        )
        return (
            f"Evaluate the confidence of these extracted values:\n"
            f"{field_desc}\n\n"
            f"Document content:\n{content[:3000]}\n\n"
            f"Rate each field as high/medium/low confidence."
        )

    def _parse_result(
        self,
        result: dict[str, Any],
        fields: list[ExtractedField],
    ) -> JudgeResult:
        """Parse the LLM result into JudgeResult.

        Uses structured_response from DeepAgents SDK when available.
        Falls back to heuristic assessment otherwise.
        """
        structured = result.get("structured_response")
        if structured is not None and isinstance(structured, JudgeResult):
            return structured

        # Fallback: heuristic-based assessment
        return self._build_heuristic_result(fields)

    def _build_heuristic_result(self, fields: list[ExtractedField]) -> JudgeResult:
        """Build JudgeResult using heuristic confidence assessment."""
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

    def as_subagent_config(self) -> SubAgent:
        """Create a subagent config dict for registration with orchestrator."""
        return SubAgent(
            name="judge",
            description="Evaluates extraction confidence per field",
            system_prompt="You are an extraction quality judge.",
            tools=[],
            model="openai:gpt-5.4-mini",
        )
