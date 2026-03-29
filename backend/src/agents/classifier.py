"""Classifier subagent for document classification.

Uses the DeepAgents SDK to classify parsed documents against
user-defined categories. Applies PII middleware before LLM calls.
"""

from __future__ import annotations

import uuid
from typing import Any

from deepagents import SubAgent, create_deep_agent

from src.agents.middleware.pii_filter import PIIFilterMiddleware
from src.agents.schemas.classification import ClassificationResult


async def _get_categories_tool(categories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tool: get available categories for classification."""
    return categories


async def _get_parsed_content_tool(content: str) -> str:
    """Tool: get parsed document content for classification."""
    return content


class ClassifierSubagent:
    """Subagent that classifies documents into user-defined categories."""

    def __init__(self) -> None:
        self._pii_filter = PIIFilterMiddleware()
        self._agent = create_deep_agent(
            model="openai:gpt-5.4-mini",
            tools=[self._get_categories, self._get_parsed_content],
            system_prompt=(
                "You are a document classifier for a PE document intelligence system. "
                "Given a document and a list of categories with their criteria, "
                "classify the document into the single best-matching category. "
                "Return the category_id, category_name, and reasoning."
            ),
            response_format=ClassificationResult,
        )
        self._categories: list[dict[str, Any]] = []
        self._parsed_content: str = ""

    async def classify(
        self,
        parsed_content: str,
        categories: list[dict[str, Any]],
    ) -> ClassificationResult:
        """Classify a document against available categories.

        Args:
            parsed_content: The parsed markdown content.
            categories: List of category dicts with id, name, criteria.

        Returns:
            ClassificationResult with matched category and reasoning.
        """
        self._categories = categories
        filtered = self._pii_filter.filter_content(parsed_content)
        self._parsed_content = filtered.redacted_text

        if not categories:
            return ClassificationResult(
                category_id=uuid.uuid4(),
                category_name="Other/Unclassified",
                reasoning="No categories defined in the system.",
            )

        prompt = self._build_prompt(filtered.redacted_text, categories)
        result = await self._agent.ainvoke(prompt)

        return self._parse_response(result, categories)

    def _build_prompt(self, content: str, categories: list[dict[str, Any]]) -> str:
        """Build the classification prompt."""
        cat_descriptions = "\n".join(
            f"- {c['name']} (id={c['id']}): {c.get('classification_criteria', 'N/A')}"
            for c in categories
        )
        return (
            f"Classify the following document into one of these categories:\n"
            f"{cat_descriptions}\n\n"
            f"Document content:\n{content[:3000]}\n\n"
            f"Return the best matching category."
        )

    def _parse_response(
        self,
        result: dict[str, Any],
        categories: list[dict[str, Any]],
    ) -> ClassificationResult:
        """Parse agent response into ClassificationResult.

        Uses structured_response from the DeepAgents SDK when available.
        Falls back to first category if structured parsing fails.
        """
        structured = result.get("structured_response")
        if structured is not None and isinstance(structured, ClassificationResult):
            return structured

        # Fallback: try to match from raw response text
        response_text = result.get("response", "")
        for cat in categories:
            if cat["name"].lower() in response_text.lower():
                return ClassificationResult(
                    category_id=cat["id"],
                    category_name=cat["name"],
                    reasoning=response_text or "Classification based on content analysis.",
                )

        # Final fallback: first category
        if categories:
            cat = categories[0]
            return ClassificationResult(
                category_id=cat["id"],
                category_name=cat["name"],
                reasoning=response_text or "Classification based on content analysis.",
            )

        return ClassificationResult(
            category_id=uuid.uuid4(),
            category_name="Other/Unclassified",
            reasoning="No matching category found.",
        )

    async def _get_categories(self) -> list[dict[str, Any]]:
        """Tool: get available categories."""
        return self._categories

    async def _get_parsed_content(self) -> str:
        """Tool: get parsed document content."""
        return self._parsed_content

    def as_subagent_config(self) -> SubAgent:
        """Create a subagent config dict for registration with orchestrator."""
        return SubAgent(
            name="classifier",
            description="Classifies documents into user-defined categories",
            system_prompt="You are a document classifier.",
            tools=[],
            model="openai:gpt-5.4-mini",
        )
