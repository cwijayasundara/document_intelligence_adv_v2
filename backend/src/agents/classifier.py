"""Classifier subagent for document classification.

Uses the DeepAgent stub to classify parsed documents against
user-defined categories. Applies PII middleware before LLM calls.
"""

from __future__ import annotations

import uuid
from typing import Any

from src.agents.deepagents_stub import SubAgentSlot, create_deep_agent
from src.agents.middleware.pii_filter import PIIFilterMiddleware
from src.agents.schemas.classification import ClassificationResult


class ClassifierSubagent:
    """Subagent that classifies documents into user-defined categories."""

    def __init__(self) -> None:
        self._pii_filter = PIIFilterMiddleware()
        self._agent = create_deep_agent(
            model="openai:gpt-5.4-mini",
            tools=[self._get_categories, self._get_parsed_content],
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
        response = await self._agent.run(prompt)

        return self._parse_response(response, categories)

    def _build_prompt(self, content: str, categories: list[dict[str, Any]]) -> str:
        """Build the classification prompt."""
        cat_descriptions = "\n".join(
            f"- {c['name']}: {c.get('classification_criteria', 'N/A')}" for c in categories
        )
        return (
            f"Classify the following document into one of these categories:\n"
            f"{cat_descriptions}\n\n"
            f"Document content:\n{content[:3000]}\n\n"
            f"Return the best matching category."
        )

    def _parse_response(
        self,
        response: dict[str, Any],
        categories: list[dict[str, Any]],
    ) -> ClassificationResult:
        """Parse agent response into ClassificationResult.

        Falls back to first category or 'Other/Unclassified'.
        """
        if categories:
            cat = categories[0]
            return ClassificationResult(
                category_id=cat["id"],
                category_name=cat["name"],
                reasoning=response.get("response", "Classification based on content analysis."),
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

    def as_subagent_slot(self) -> SubAgentSlot:
        """Create a SubAgentSlot for registration with orchestrator."""
        return SubAgentSlot(
            name="classifier",
            agent=self._agent,
            description="Classifies documents into user-defined categories",
        )
