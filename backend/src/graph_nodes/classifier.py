"""Classifier module for document classification.

Uses a hybrid approach combining file name signals and document content
(preferring summary when available) for accurate PE document classification.
Applies PII middleware before LLM calls. Returns confidence scores.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.graph_nodes.llm import get_llm
from src.graph_nodes.middleware.decorators import with_retry, with_telemetry
from src.graph_nodes.middleware.pii_filter import PIIFilterMiddleware
from src.graph_nodes.schemas.classification import ClassificationResult

logger = logging.getLogger(__name__)

# File name patterns that hint at document category
_FILENAME_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bLPA\b|Limited.?Partnership.?Agreement", re.IGNORECASE), "Limited Partnership Agreement"),
    (re.compile(r"\bSub(?:scription)?.?(?:Agree|Doc)", re.IGNORECASE), "Subscription Agreement"),
    (re.compile(r"\bSide.?Letter\b|\bSL\b", re.IGNORECASE), "Side Letter"),
]

_SYSTEM_PROMPT = """\
You are an expert document classifier for a Private Equity document intelligence platform.

Your task: classify a PE document into exactly ONE of the provided categories.

## Classification Guidelines

- Examine the document content carefully for structural and legal indicators.
- Use the file name as a supporting signal, but content always takes priority.
- If the file name suggests one category but the content clearly indicates another, follow the content.
- Return a confidence score from 0 to 100:
  - 90-100: Strong match — multiple defining attributes present
  - 70-89: Good match — key attributes present but some missing
  - 50-69: Moderate match — some indicators present, ambiguous
  - Below 50: Weak match — few indicators, likely a guess

## Category Examples

**Limited Partnership Agreement (LPA):**
Typically titled "Limited Partnership Agreement" or "Agreement of Limited Partnership".
Contains: fund name, GP/LP structure, management fee rate (e.g. 1.5-2%), carried interest
(typically 20%), preferred return (typically 8%), fund term (e.g. 10 years), commitment period,
distribution waterfall, capital call mechanics, clawback provisions, key person clauses.

**Subscription Agreement:**
Agreement by which an LP commits capital. Contains: capital commitment amount, investor
representations & warranties, accredited investor certification, tax ID, AML/KYC certifications,
subscription amount, references to the main LPA.

**Side Letter:**
Supplemental agreement between GP and a specific LP. References the main LPA by name.
Contains: fee discounts/waivers, MFN clauses, co-investment rights, enhanced reporting,
excuse/exclusion rights, transfer restriction modifications.

Return the category_id, category_name, confidence (0-100), and reasoning.
"""

_pii_filter = PIIFilterMiddleware()


@with_retry(max_retries=3)
@with_telemetry(node_name="classify")
async def classify_document(
    file_name: str,
    content: str,
    categories: list[dict[str, Any]],
    summary: str | None = None,
) -> ClassificationResult:
    """Classify a document against available categories.

    Uses summary when available (more focused), falls back to full content.
    File name is always included as a supporting signal.

    Args:
        file_name: Original file name of the document.
        content: The full parsed markdown content.
        categories: List of category dicts with id, name, criteria.
        summary: Optional pre-generated document summary.

    Returns:
        ClassificationResult with matched category, confidence, and reasoning.
    """
    if not categories:
        return ClassificationResult(
            category_id=uuid.uuid4(),
            category_name="Other/Unclassified",
            confidence=0,
            reasoning="No categories defined in the system.",
        )

    # Load learned corrections from long-term memory
    learned_context = await _load_learned_corrections(file_name)

    # Use summary if available, otherwise full content
    classification_text = summary if summary else content
    filtered = _pii_filter.filter_content(classification_text)

    prompt = _build_prompt(
        file_name=file_name,
        content=filtered.redacted_text,
        categories=categories,
        is_summary=summary is not None,
        learned_context=learned_context,
    )

    try:
        llm = get_llm()
        result = await llm.with_structured_output(ClassificationResult).ainvoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        if result is not None:
            return result
    except Exception:
        logger.exception("Structured output parsing failed, falling back to text match")

    return _parse_fallback("", categories)


def _build_prompt(
    file_name: str,
    content: str,
    categories: list[dict[str, Any]],
    is_summary: bool,
    learned_context: str = "",
) -> str:
    """Build the classification prompt with file name + content."""
    cat_descriptions = "\n".join(
        f"- **{c['name']}** (id={c['id']}): "
        f"{c.get('classification_criteria', 'No specific criteria defined.')}"
        for c in categories
    )

    file_name_hint = _get_filename_hint(file_name)
    hint_line = (
        f"File name analysis suggests: **{file_name_hint}** "
        "(use as a supporting signal only, content takes priority)\n\n"
        if file_name_hint
        else ""
    )

    content_label = "Document summary" if is_summary else "Document content"

    learned_block = ""
    if learned_context:
        learned_block = f"## Learned corrections\n{learned_context}\n\n"

    return (
        f"{learned_block}"
        f"## File Name\n{file_name}\n\n"
        f"{hint_line}"
        f"## Available Categories\n{cat_descriptions}\n\n"
        f"## {content_label}\n{content}\n\n"
        f"Classify this document into the single best-matching category. "
        f"Return category_id, category_name, confidence (0-100), and reasoning."
    )


def _get_filename_hint(file_name: str) -> str | None:
    """Extract a category hint from the file name, if any pattern matches."""
    for pattern, category_name in _FILENAME_HINTS:
        if pattern.search(file_name):
            return category_name
    return None


def _parse_fallback(
    response_text: str,
    categories: list[dict[str, Any]],
) -> ClassificationResult:
    """Fallback parsing when structured output fails."""
    # Try to match category from raw response text
    for cat in categories:
        if cat["name"].lower() in response_text.lower():
            return ClassificationResult(
                category_id=cat["id"],
                category_name=cat["name"],
                confidence=50,
                reasoning=response_text or "Classified via text matching fallback.",
            )

    # Final fallback: Other/Unclassified if it exists, else first category
    other = next((c for c in categories if "unclassified" in c["name"].lower()), None)
    fallback = other or categories[0]
    return ClassificationResult(
        category_id=fallback["id"],
        category_name=fallback["name"],
        confidence=20,
        reasoning=response_text or "Low confidence — no strong category match found.",
    )


async def _load_learned_corrections(file_name: str) -> str:
    """Load classification corrections from long-term memory."""
    try:
        from src.graph_nodes.memory.store import load_corrections

        entries = await load_corrections(
            user_id="system", correction_type="classification"
        )
        if not entries:
            return ""
        lines = []
        for data in entries:
            lines.append(
                f"- File pattern '{data.get('file_pattern', '')}' "
                f"should be classified as '{data.get('correct_category', '')}' "
                f"(reason: {data.get('reason', 'user correction')})"
            )
        return "\n".join(lines)
    except Exception:
        return ""
