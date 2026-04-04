"""Summarizer subagent for document summarization.

Generates concise summaries with key topics extracted from
parsed document content. Applies PII middleware.
"""

from __future__ import annotations

from typing import Any

from deepagents import SubAgent

from src.agents.factory import create_agent

from src.agents.middleware.pii_filter import PIIFilterMiddleware
from src.agents.schemas.summary import SummaryResult

# PE-specific attributes the summary MUST preserve for downstream classification
_PE_ATTRIBUTES = """
When summarizing PE (Private Equity) documents, you MUST explicitly preserve
and include any of the following attributes found in the document:
- Fund Name (full legal name of the fund)
- General Partner (GP entity name)
- Limited Partners (LP names or descriptions)
- Management Fee Rate (percentage)
- Carried Interest Rate (percentage)
- Preferred Return / Hurdle Rate (percentage)
- Fund Term (duration and extension provisions)
- Commitment Period / Investment Period
- Distribution Waterfall structure
- Governing Law / Jurisdiction
- Capital Commitment amounts
- Key Person provisions
- Clawback provisions
- Investor representations and warranties
- Fee discounts or waivers
- Most-Favored-Nation (MFN) clauses
- Co-investment rights

If the document is not a PE document, summarize it normally.
"""


class SummarizerSubagent:
    """Subagent that generates document summaries with key topics."""

    def __init__(self) -> None:
        self._pii_filter = PIIFilterMiddleware()
        self._agent = create_agent(
            model="openai:gpt-5.4-mini",
            tools=[self._get_parsed_content],
            system_prompt=(
                "You are a document summarizer for a PE document intelligence system. "
                "Given a document, produce a thorough summary that retains all "
                "financially and legally significant details, and identify the key topics. "
                "Return the summary and key_topics.\n\n"
                f"{_PE_ATTRIBUTES}"
            ),
            response_format=SummaryResult,
            name="summarizer",
        )
        self._parsed_content: str = ""

    async def summarize(self, parsed_content: str) -> SummaryResult:
        """Generate a summary of the document content.

        Args:
            parsed_content: The full parsed markdown content.

        Returns:
            SummaryResult with summary and key topics.
        """
        filtered = self._pii_filter.filter_content(parsed_content)
        self._parsed_content = filtered.redacted_text

        prompt = self._build_prompt(filtered.redacted_text)
        result = await self._agent.ainvoke({"messages": [{"role": "user", "content": prompt}]})

        return self._parse_result(result, filtered.redacted_text)

    def _build_prompt(self, content: str) -> str:
        """Build the summarization prompt using full document content."""
        return (
            "Summarize the following document thoroughly. "
            "Preserve all key financial terms, legal provisions, party names, "
            "percentages, dates, and structural details. "
            "Identify and list the key topics.\n\n"
            f"{content}\n\n"
            "Provide a comprehensive summary and list of key topics."
        )

    def _parse_result(self, result: dict[str, Any], content: str) -> SummaryResult:
        """Parse the LLM result into SummaryResult.

        Uses structured_response from DeepAgents SDK when available.
        Falls back to extracting text from the last message in LangGraph state.
        """
        # Check for structured response
        structured = result.get("structured_response")
        if structured is not None and isinstance(structured, SummaryResult):
            return structured

        # Extract text from LangGraph messages state
        response_text = ""
        messages = result.get("messages", [])
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "content"):
                response_text = last_msg.content
            elif isinstance(last_msg, dict):
                response_text = last_msg.get("content", "")

        if not response_text:
            response_text = result.get(
                "response",
                "Document summary generated from parsed content.",
            )

        return SummaryResult(
            summary=response_text,
            key_topics=self._extract_topics(content),
        )

    @staticmethod
    def _extract_topics(content: str) -> list[str]:
        """Extract key topics from content via keyword matching."""
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

    def as_subagent_config(self) -> SubAgent:
        """Create a subagent config dict for registration with orchestrator."""
        return SubAgent(
            name="summarizer",
            description="Generates document summaries with key topics",
            system_prompt="You are a document summarizer.",
            tools=[],
            model="openai:gpt-5.4-mini",
        )
