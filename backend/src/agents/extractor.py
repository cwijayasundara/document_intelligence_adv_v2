"""Extractor subagent for structured field extraction.

Dynamically builds Pydantic models from extraction field schemas
and extracts values with source text citations from parsed document content.
"""

from __future__ import annotations

from typing import Any

from deepagents import SubAgent, create_deep_agent
from pydantic import BaseModel, Field, create_model

from src.agents.middleware.pii_filter import PIIFilterMiddleware
from src.agents.schemas.extraction import ExtractedField, ExtractionResult

DATA_TYPE_MAP: dict[str, type] = {
    "string": str,
    "number": float,
    "date": str,
    "currency": str,
    "percentage": str,
}

_SYSTEM_PROMPT = """\
You are a field extractor for a Private Equity document intelligence system.

For each requested field, you must:
1. Find the value in the document
2. Quote the EXACT passage from the document that contains or supports the value

Rules:
- The source quote must be copied verbatim from the document — do not paraphrase
- Include enough surrounding context in the source quote to make it meaningful \
(typically 1-2 sentences)
- If a field cannot be found, set both the value and source to empty strings
- For percentage fields, include the % symbol
- For date fields, preserve the original format from the document
"""


def build_dynamic_model(
    fields: list[dict[str, Any]],
) -> type[BaseModel]:
    """Build a Pydantic model with value + source pairs per field.

    For each extraction field, creates two model fields:
      - {field_name}: the extracted value
      - {field_name}_source: the verbatim source text from the document
    """
    field_definitions: dict[str, Any] = {}
    for f in fields:
        python_type = DATA_TYPE_MAP.get(f.get("data_type", "string"), str)
        name = f["field_name"]

        # Value field
        field_definitions[name] = (
            python_type | None,
            Field(default=None, description=f.get("description", "")),
        )
        # Source text field
        field_definitions[f"{name}_source"] = (
            str | None,
            Field(
                default=None,
                description=f"Verbatim quote from the document supporting the {name} value",
            ),
        )

    return create_model("DynamicExtractionModel", **field_definitions)


class ExtractorSubagent:
    """Subagent that extracts structured fields with source citations."""

    def __init__(self) -> None:
        self._pii_filter = PIIFilterMiddleware()

    async def extract(
        self,
        parsed_content: str,
        extraction_fields: list[dict[str, Any]],
    ) -> ExtractionResult:
        """Extract fields from parsed document content.

        Args:
            parsed_content: The parsed markdown content.
            extraction_fields: Field definitions from the extraction schema.

        Returns:
            ExtractionResult with extracted values and source text.
        """
        filtered = self._pii_filter.filter_content(parsed_content)

        if not extraction_fields:
            return ExtractionResult(fields=[])

        dynamic_model = build_dynamic_model(extraction_fields)

        extraction_agent = create_deep_agent(
            model="openai:gpt-5.4-mini",
            tools=[],
            system_prompt=_SYSTEM_PROMPT,
            response_format=dynamic_model,
        )

        prompt = self._build_prompt(filtered.redacted_text, extraction_fields)
        result = await extraction_agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]}
        )

        return self._build_result(result, extraction_fields)

    def _build_prompt(self, content: str, fields: list[dict[str, Any]]) -> str:
        """Build the extraction prompt."""
        parts = []
        for f in fields:
            line = (
                f"- **{f['field_name']}** ({f.get('data_type', 'string')}): "
                f"{f.get('description', 'N/A')}"
            )
            examples = f.get("examples")
            if examples:
                line += f" — Examples: {examples}"
            parts.append(line)
        field_desc = "\n".join(parts)
        return (
            f"Extract the following fields from the document. "
            f"For each field, provide the extracted value AND a verbatim quote "
            f"from the document that contains or supports the value.\n\n"
            f"## Fields to extract\n{field_desc}\n\n"
            f"## Document\n{content}\n\n"
            f"Return each field's value and its source quote from the document."
        )

    def _build_result(
        self,
        result: dict[str, Any],
        fields: list[dict[str, Any]],
    ) -> ExtractionResult:
        """Build ExtractionResult from the LLM response."""
        structured = result.get("structured_response")
        extracted = []

        for f in fields:
            name = f["field_name"]
            if structured is not None:
                value = getattr(structured, name, None)
                source = getattr(structured, f"{name}_source", None)
            else:
                value = None
                source = None

            extracted.append(
                ExtractedField(
                    field_name=name,
                    extracted_value=str(value) if value is not None else "",
                    source_text=str(source) if source is not None else "",
                )
            )

        return ExtractionResult(fields=extracted)

    def as_subagent_config(self) -> SubAgent:
        """Create a subagent config dict for registration with orchestrator."""
        return SubAgent(
            name="extractor",
            description="Extracts structured fields from documents",
            system_prompt="You are a field extractor.",
            tools=[],
            model="openai:gpt-5.4-mini",
        )
