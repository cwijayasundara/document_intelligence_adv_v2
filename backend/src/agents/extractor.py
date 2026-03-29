"""Extractor subagent for structured field extraction.

Dynamically builds Pydantic models from extraction field schemas
and extracts values from parsed document content.
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


def build_dynamic_model(
    fields: list[dict[str, Any]],
) -> type[BaseModel]:
    """Build a Pydantic model dynamically from extraction field definitions.

    Args:
        fields: List of field dicts with field_name, data_type, description.

    Returns:
        A dynamically created Pydantic model class.
    """
    field_definitions: dict[str, Any] = {}
    for f in fields:
        python_type = DATA_TYPE_MAP.get(f.get("data_type", "string"), str)
        field_definitions[f["field_name"]] = (
            python_type | None,
            Field(
                default=None,
                description=f.get("description", ""),
            ),
        )

    return create_model("DynamicExtractionModel", **field_definitions)


class ExtractorSubagent:
    """Subagent that extracts structured fields from documents.

    Builds a dynamic Pydantic model from the category's extraction schema
    and uses DeepAgent for structured output extraction.
    """

    def __init__(self) -> None:
        self._pii_filter = PIIFilterMiddleware()
        self._agent = create_deep_agent(
            model="openai:gpt-5.4-mini",
            tools=[self._get_extraction_schema, self._get_parsed_content],
            system_prompt=(
                "You are a field extractor for a PE document intelligence system. "
                "Given a document and a list of fields to extract, find the value "
                "of each field in the document along with the source text that "
                "supports the extraction."
            ),
        )
        self._schema_fields: list[dict[str, Any]] = []
        self._parsed_content: str = ""

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
            ExtractionResult with extracted values.
        """
        self._schema_fields = extraction_fields
        filtered = self._pii_filter.filter_content(parsed_content)
        self._parsed_content = filtered.redacted_text

        if not extraction_fields:
            return ExtractionResult(fields=[])

        dynamic_model = build_dynamic_model(extraction_fields)

        # Create a per-extraction agent with the dynamic response format
        extraction_agent = create_deep_agent(
            model="openai:gpt-5.4-mini",
            tools=[self._get_extraction_schema, self._get_parsed_content],
            system_prompt=(
                "You are a field extractor for a PE document intelligence system. "
                "Extract the requested fields from the document content. "
                "Return the extracted values in the structured format."
            ),
            response_format=dynamic_model,
        )

        prompt = self._build_prompt(filtered.redacted_text, extraction_fields)
        result = await extraction_agent.ainvoke(prompt)

        return self._build_result(result, extraction_fields)

    def _build_prompt(self, content: str, fields: list[dict[str, Any]]) -> str:
        """Build the extraction prompt."""
        field_desc = "\n".join(
            f"- {f['field_name']} ({f.get('data_type', 'string')}): {f.get('description', 'N/A')}"
            for f in fields
        )
        return (
            f"Extract the following fields from the document:\n"
            f"{field_desc}\n\n"
            f"Document content:\n{content[:4000]}\n\n"
            f"Return the extracted values with source text."
        )

    def _build_result(
        self,
        result: dict[str, Any],
        fields: list[dict[str, Any]],
    ) -> ExtractionResult:
        """Build ExtractionResult from the LLM response."""
        structured = result.get("structured_response")
        extracted = []

        if structured is not None:
            # structured is a Pydantic model instance from the dynamic model
            for f in fields:
                field_name = f["field_name"]
                value = getattr(structured, field_name, None)
                extracted.append(
                    ExtractedField(
                        field_name=field_name,
                        extracted_value=str(value) if value is not None else "",
                        source_text="",
                    )
                )
        else:
            # Fallback: return empty fields
            for f in fields:
                extracted.append(
                    ExtractedField(
                        field_name=f["field_name"],
                        extracted_value="",
                        source_text="",
                    )
                )

        return ExtractionResult(fields=extracted)

    async def _get_extraction_schema(self) -> list[dict[str, Any]]:
        """Tool: get extraction schema fields."""
        return self._schema_fields

    async def _get_parsed_content(self) -> str:
        """Tool: get parsed document content."""
        return self._parsed_content

    def as_subagent_config(self) -> SubAgent:
        """Create a subagent config dict for registration with orchestrator."""
        return SubAgent(
            name="extractor",
            description="Extracts structured fields from documents",
            system_prompt="You are a field extractor.",
            tools=[],
            model="openai:gpt-5.4-mini",
        )
