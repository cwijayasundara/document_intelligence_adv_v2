"""Summarizer module for document summarization.

Generates concise summaries with key topics extracted from
parsed document content. Applies PII filtering.
"""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from src.graph_nodes.llm import get_llm
from src.graph_nodes.middleware.decorators import with_retry, with_telemetry
from src.graph_nodes.middleware.pii_filter import PIIFilterMiddleware
from src.graph_nodes.schemas.summary import SummaryResult

logger = logging.getLogger(__name__)

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

_SYSTEM_PROMPT = (
    "You are a document summarizer for a PE document intelligence system. "
    "Given a document, produce a thorough summary that retains all "
    "financially and legally significant details, and identify the key topics. "
    "Return the summary and key_topics.\n\n"
    f"{_PE_ATTRIBUTES}"
)

_pii_filter = PIIFilterMiddleware()


def _build_prompt(content: str) -> str:
    """Build the summarization prompt using full document content."""
    return (
        "Summarize the following document thoroughly. "
        "Preserve all key financial terms, legal provisions, party names, "
        "percentages, dates, and structural details. "
        "Identify and list the key topics.\n\n"
        f"{content}\n\n"
        "Provide a comprehensive summary and list of key topics."
    )


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


@with_retry(max_retries=3)
@with_telemetry(node_name="summarize")
async def summarize_document(parsed_content: str) -> SummaryResult:
    """Generate a summary of the document content.

    Args:
        parsed_content: The full parsed markdown content.

    Returns:
        SummaryResult with summary and key topics.
    """
    filtered = _pii_filter.filter_content(parsed_content)
    redacted = filtered.redacted_text

    prompt = _build_prompt(redacted)

    try:
        llm = get_llm()
        result = await llm.with_structured_output(SummaryResult).ainvoke(
            [
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )
        if result is not None:
            return result
    except Exception:
        logger.exception("Structured output parsing failed, falling back to extraction")

    # Fallback: return a basic result with keyword-extracted topics
    return SummaryResult(
        summary="Document summary generated from parsed content.",
        key_topics=_extract_topics(redacted),
    )
