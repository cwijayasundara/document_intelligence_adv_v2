"""PII filtering middleware for redacting sensitive information.

Redacts SSN/tax IDs, phone numbers, email addresses, bank accounts,
and US street addresses while preserving fund names and financial terms.
Supports configurable strategies: REDACT, MASK, and BLOCK.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field


class PIIStrategy(enum.Enum):
    """Strategy for handling detected PII."""

    REDACT = "redact"
    MASK = "mask"
    BLOCK = "block"


class PIIDetectedError(Exception):
    """Raised when PII is detected and strategy is BLOCK."""


# Financial terms that should NOT be redacted
PASSTHROUGH_TERMS = {
    "management fee",
    "carried interest",
    "preferred return",
    "fund term",
    "commitment period",
    "capital call",
    "distribution",
    "net asset value",
    "internal rate of return",
    "hurdle rate",
}

# Pattern: SSN (XXX-XX-XXXX)
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

# Pattern: Phone numbers - (XXX) XXX-XXXX or XXX-XXX-XXXX
PHONE_PATTERN = re.compile(r"\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}\b")

# Pattern: Email addresses
EMAIL_PATTERN = re.compile(r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b")

# Pattern: Bank account / routing numbers (8-17 digit sequences)
ACCOUNT_PATTERN = re.compile(r"\b\d{8,17}\b")

# Pattern: US street addresses (number + street name + type)
ADDRESS_PATTERN = re.compile(
    r"\b\d{1,5}\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*"
    r"\s+(?:Street|St|Avenue|Ave|Boulevard|Blvd|Drive|Dr|Lane|Ln"
    r"|Road|Rd|Court|Ct|Circle|Cir|Way|Place|Pl)\b",
    re.IGNORECASE,
)


@dataclass
class PIIFilterResult:
    """Result of PII filtering."""

    redacted_text: str
    redactions_count: int
    redaction_types: dict[str, int] = field(default_factory=dict)


class PIIFilterMiddleware:
    """Middleware that filters PII from content before LLM calls.

    Detects and redacts SSN, phone, email, bank accounts, and addresses
    with typed placeholders. Preserves fund names and financial terms.
    """

    def __init__(self, strategy: PIIStrategy = PIIStrategy.REDACT) -> None:
        self._strategy = strategy
        # Order matters: more specific patterns first to avoid overlap
        self._patterns: list[tuple[re.Pattern[str], str, str]] = [
            (SSN_PATTERN, "[REDACTED_SSN]", "ssn"),
            (EMAIL_PATTERN, "[REDACTED_EMAIL]", "email"),
            (ADDRESS_PATTERN, "[REDACTED_ADDRESS]", "address"),
            (ACCOUNT_PATTERN, "[REDACTED_ACCOUNT]", "account"),
            (PHONE_PATTERN, "[REDACTED_PHONE]", "phone"),
        ]

    def filter_content(self, text: str) -> PIIFilterResult:
        """Filter PII from text content.

        Args:
            text: Raw text that may contain PII.

        Returns:
            PIIFilterResult with redacted text and stats.

        Raises:
            PIIDetectedError: If strategy is BLOCK and PII is found.
        """
        redacted = text
        total_count = 0
        type_counts: dict[str, int] = {}

        for pattern, replacement, pii_type in self._patterns:
            matches = pattern.findall(redacted)
            if matches:
                filtered_matches = [m for m in matches if not self._is_financial_term(m, redacted)]
                if filtered_matches:
                    count = len(filtered_matches)
                    total_count += count
                    type_counts[pii_type] = type_counts.get(pii_type, 0) + count

                    if self._strategy == PIIStrategy.BLOCK:
                        continue  # count all types before raising

                    if self._strategy == PIIStrategy.MASK:
                        redacted = pattern.sub(
                            lambda m, pt=pii_type: (
                                self._mask_match(m.group(), pt)
                                if not self._is_financial_term(m.group(), redacted)
                                else m.group()
                            ),
                            redacted,
                        )
                    else:  # REDACT (default)
                        redacted = pattern.sub(
                            lambda m, rep=replacement: (
                                rep
                                if not self._is_financial_term(m.group(), redacted)
                                else m.group()
                            ),
                            redacted,
                        )

        if self._strategy == PIIStrategy.BLOCK and total_count > 0:
            detected = ", ".join(type_counts.keys())
            raise PIIDetectedError(f"PII detected ({detected}): {total_count} instance(s) found")

        return PIIFilterResult(
            redacted_text=redacted,
            redactions_count=total_count,
            redaction_types=type_counts,
        )

    @staticmethod
    def _mask_match(match_text: str, pii_type: str) -> str:
        """Mask PII preserving last 4 characters.

        Args:
            match_text: The matched PII text.
            pii_type: The type of PII detected.

        Returns:
            Masked text with last 4 chars preserved.
        """
        if len(match_text) <= 4:
            return "*" * len(match_text)
        tail = match_text[-4:]
        head = match_text[:-4]
        masked_head = re.sub(r"[a-zA-Z0-9]", "*", head)
        return masked_head + tail

    @staticmethod
    def _is_financial_term(match_text: str, full_text: str) -> bool:
        """Check if a match is part of a financial term to preserve."""
        lower_text = full_text.lower()
        lower_match = match_text.lower().strip()
        for term in PASSTHROUGH_TERMS:
            if lower_match in term or term in lower_text:
                # Check if the match is adjacent to the financial term
                idx = lower_text.find(lower_match)
                if idx >= 0:
                    context_start = max(0, idx - 30)
                    context_end = min(len(lower_text), idx + len(lower_match) + 30)
                    context = lower_text[context_start:context_end]
                    if term in context:
                        return True
        return False
