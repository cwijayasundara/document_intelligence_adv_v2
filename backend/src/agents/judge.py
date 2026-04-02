"""Judge subagent for confidence scoring of extracted values.

Evaluates extraction quality using source text citations and field metadata.
Returns confidence ratings with reasoning per field.
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

_SYSTEM_PROMPT = """\
You are an extraction quality judge for a Private Equity document intelligence system.

Evaluate each extracted field by checking:
1. **Source match**: Does the extracted value appear in or follow logically from the \
quoted source text?
2. **Format validity**: Does the value match the expected data type (e.g. percentage \
fields should have %, dates should be parseable)?
3. **Completeness**: Is the full value captured, or is it truncated/partial?
4. **Source quality**: Is the source quote a verbatim passage from the document, or \
does it look fabricated?

Confidence levels:
- **high**: Value is directly stated in the source quote, correct format, complete
- **medium**: Value is implied by the source but not stated verbatim, or format is \
slightly off, or source context is ambiguous
- **low**: Value has no supporting source, is empty, wrong format, or source looks \
fabricated

Return a confidence level and reasoning for each field.
"""


class JudgeSubagent:
    """Subagent that evaluates extraction quality with confidence scoring."""

    def __init__(self) -> None:
        self._pii_filter = PIIFilterMiddleware()
        self._agent = create_deep_agent(
            model="openai:gpt-5.4-mini",
            tools=[],
            system_prompt=_SYSTEM_PROMPT,
            response_format=JudgeResult,
        )

    async def evaluate(
        self,
        extracted_fields: list[ExtractedField],
        parsed_content: str,
        field_metadata: list[dict[str, Any]] | None = None,
    ) -> JudgeResult:
        """Evaluate extraction quality for each field.

        Args:
            extracted_fields: List of extracted field values with source text.
            parsed_content: Full document content for cross-reference.
            field_metadata: Optional field definitions with data_type, required, examples.

        Returns:
            JudgeResult with confidence evaluations per field.
        """
        filtered = self._pii_filter.filter_content(parsed_content)

        if not extracted_fields:
            return JudgeResult(evaluations=[])

        prompt = self._build_prompt(
            extracted_fields, filtered.redacted_text, field_metadata
        )
        result = await self._agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]}
        )

        return self._parse_result(result, extracted_fields)

    def _build_prompt(
        self,
        fields: list[ExtractedField],
        content: str,
        field_metadata: list[dict[str, Any]] | None = None,
    ) -> str:
        """Build the judge evaluation prompt with source text and field metadata."""
        meta_map: dict[str, dict[str, Any]] = {}
        if field_metadata:
            meta_map = {m["field_name"]: m for m in field_metadata}

        field_sections = []
        for f in fields:
            meta = meta_map.get(f.field_name, {})
            data_type = meta.get("data_type", "string")
            required = meta.get("required", False)
            examples = meta.get("examples", "")

            section = (
                f"### {f.field_name}\n"
                f"- **Expected type**: {data_type}"
                f"{' (required)' if required else ''}\n"
                f"- **Extracted value**: {f.extracted_value or '(empty)'}\n"
                f"- **Source quote**: {f.source_text or '(none provided)'}\n"
            )
            if examples:
                section += f"- **Example values**: {examples}\n"
            field_sections.append(section)

        fields_block = "\n".join(field_sections)

        return (
            f"## Extracted Fields to Evaluate\n\n{fields_block}\n\n"
            f"## Original Document (for cross-reference)\n{content}\n\n"
            f"For each field, verify the extracted value against the source quote "
            f"and the original document. Return confidence (high/medium/low) and reasoning."
        )

    def _parse_result(
        self,
        result: dict[str, Any],
        fields: list[ExtractedField],
    ) -> JudgeResult:
        """Parse the LLM result into JudgeResult."""
        structured = result.get("structured_response")
        if structured is not None and isinstance(structured, JudgeResult):
            return structured

        # Fallback: heuristic-based assessment using source text
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
                    reasoning=self._default_reasoning(f, confidence),
                )
            )
        return JudgeResult(evaluations=evaluations)

    @staticmethod
    def _assess_confidence(field: ExtractedField) -> str:
        """Assess confidence based on extracted value and source text."""
        if not field.extracted_value:
            return CONFIDENCE_LOW
        if not field.source_text:
            return CONFIDENCE_MEDIUM
        # Check if extracted value appears in the source quote
        if field.extracted_value.lower() in field.source_text.lower():
            return CONFIDENCE_HIGH
        return CONFIDENCE_MEDIUM

    @staticmethod
    def _default_reasoning(field: ExtractedField, confidence: str) -> str:
        """Return reasoning for a confidence level."""
        if confidence == CONFIDENCE_HIGH:
            return (
                f"Value '{field.extracted_value}' appears in the source quote."
            )
        if confidence == CONFIDENCE_MEDIUM:
            if not field.source_text:
                return "Value extracted but no source quote provided for verification."
            return "Value is implied by the source text but not an exact match."
        return "No value extracted or no supporting evidence found."

    def as_subagent_config(self) -> SubAgent:
        """Create a subagent config dict for registration with orchestrator."""
        return SubAgent(
            name="judge",
            description="Evaluates extraction confidence per field",
            system_prompt="You are an extraction quality judge.",
            tools=[],
            model="openai:gpt-5.4-mini",
        )
