"""Summarizer subagent for document summarization.

Generates concise summaries with key topics extracted from
parsed document content. Applies PII middleware.
"""

from __future__ import annotations

from src.agents.deepagents_stub import SubAgentSlot, create_deep_agent
from src.agents.middleware.pii_filter import PIIFilterMiddleware
from src.agents.schemas.summary import SummaryResult


class SummarizerSubagent:
    """Subagent that generates document summaries with key topics."""

    def __init__(self) -> None:
        self._pii_filter = PIIFilterMiddleware()
        self._agent = create_deep_agent(
            model="openai:gpt-5.4-mini",
            tools=[self._get_parsed_content],
        )
        self._parsed_content: str = ""

    async def summarize(self, parsed_content: str) -> SummaryResult:
        """Generate a summary of the document content.

        Args:
            parsed_content: The parsed markdown content.

        Returns:
            SummaryResult with summary and key topics.
        """
        filtered = self._pii_filter.filter_content(parsed_content)
        self._parsed_content = filtered.redacted_text

        prompt = self._build_prompt(filtered.redacted_text)
        response = await self._agent.run(prompt)

        return SummaryResult(
            summary=response.get(
                "response",
                "Document summary generated from parsed content.",
            ),
            key_topics=self._extract_topics(filtered.redacted_text),
        )

    def _build_prompt(self, content: str) -> str:
        """Build the summarization prompt."""
        return (
            f"Summarize the following document, identifying key topics:\n\n"
            f"{content[:4000]}\n\n"
            f"Provide a concise summary and list of key topics."
        )

    @staticmethod
    def _extract_topics(content: str) -> list[str]:
        """Extract key topics from content (stub implementation)."""
        topics = []
        keywords = [
            "fund",
            "partnership",
            "management fee",
            "carried interest",
            "investor",
            "commitment",
        ]
        lower_content = content.lower()
        for keyword in keywords:
            if keyword in lower_content:
                topics.append(keyword)
        return topics if topics else ["general"]

    async def _get_parsed_content(self) -> str:
        """Tool: get parsed document content."""
        return self._parsed_content

    def as_subagent_slot(self) -> SubAgentSlot:
        """Create a SubAgentSlot for registration with orchestrator."""
        return SubAgentSlot(
            name="summarizer",
            agent=self._agent,
            description="Generates document summaries with key topics",
        )
