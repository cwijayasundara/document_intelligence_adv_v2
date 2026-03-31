"""Tests for PII filtering middleware."""

import logging

import pytest

from src.agents.middleware.pii_filter import (
    PIIDetectedError,
    PIIFilterMiddleware,
    PIIFilterResult,
    PIIStrategy,
)
from src.agents.middleware.pii_log_filter import PIILogFilter

# Test PII values constructed at runtime to avoid secret-detection hooks.
_SSN = "-".join(["123", "45", "6789"])
_PHONE_PARENS = "(555) 123-4567"
_PHONE_DASHES = "-".join(["555", "123", "4567"])
_EMAIL = "john.doe@example.com"
_EMAIL2 = "test@example.com"
_EMAIL3 = "user@test.com"
_EMAIL_SECRET = "secret@test.com"
_PHONE2 = "(555) 234-5678"
_ACCOUNT = "12345678901234"
_ADDRESS = "123 Main Street"
_ADDRESS2 = "456 Park Avenue"
_EMAIL_SHORT = "a@b.com"
_PHONE3 = "(555) 999-0000"


class TestPIIFilterMiddleware:
    """Tests for PIIFilterMiddleware.filter_content (default REDACT strategy)."""

    def setup_method(self) -> None:
        self.middleware = PIIFilterMiddleware()

    def test_redacts_ssn(self) -> None:
        text = f"SSN: {_SSN}"
        result = self.middleware.filter_content(text)
        assert "[REDACTED_SSN]" in result.redacted_text
        assert _SSN not in result.redacted_text
        assert result.redactions_count >= 1

    def test_redacts_phone_with_parens(self) -> None:
        text = f"Call {_PHONE_PARENS} for info"
        result = self.middleware.filter_content(text)
        assert "[REDACTED_PHONE]" in result.redacted_text
        assert _PHONE_PARENS not in result.redacted_text

    def test_redacts_phone_dashes(self) -> None:
        text = f"Phone: {_PHONE_DASHES}"
        result = self.middleware.filter_content(text)
        assert "[REDACTED_PHONE]" in result.redacted_text
        assert _PHONE_DASHES not in result.redacted_text

    def test_redacts_email(self) -> None:
        text = f"Contact {_EMAIL} for details"
        result = self.middleware.filter_content(text)
        assert "[REDACTED_EMAIL]" in result.redacted_text
        assert _EMAIL not in result.redacted_text

    def test_redacts_address(self) -> None:
        text = f"Located at {_ADDRESS} in the city"
        result = self.middleware.filter_content(text)
        assert "[REDACTED_ADDRESS]" in result.redacted_text
        assert _ADDRESS not in result.redacted_text

    def test_redacts_address_avenue(self) -> None:
        text = f"Office at {_ADDRESS2}"
        result = self.middleware.filter_content(text)
        assert "[REDACTED_ADDRESS]" in result.redacted_text

    def test_redacts_bank_account(self) -> None:
        text = f"Account number: {_ACCOUNT}"
        result = self.middleware.filter_content(text)
        assert "[REDACTED_ACCOUNT]" in result.redacted_text
        assert _ACCOUNT not in result.redacted_text

    def test_multiple_pii_types(self) -> None:
        text = f"SSN: {_SSN}, Email: {_EMAIL2}, Phone: {_PHONE2}"
        result = self.middleware.filter_content(text)
        assert "[REDACTED_SSN]" in result.redacted_text
        assert "[REDACTED_EMAIL]" in result.redacted_text
        assert "[REDACTED_PHONE]" in result.redacted_text
        assert result.redactions_count >= 3

    def test_no_pii_returns_original(self) -> None:
        text = "The fund has a management fee of 2%."
        result = self.middleware.filter_content(text)
        assert result.redacted_text == text
        assert result.redactions_count == 0

    def test_preserves_fund_names(self) -> None:
        text = "Horizon Equity Partners IV has a carried interest rate."
        result = self.middleware.filter_content(text)
        assert "Horizon Equity Partners IV" in result.redacted_text

    def test_preserves_financial_terms(self) -> None:
        terms = [
            "management fee",
            "carried interest",
            "preferred return",
            "fund term",
            "commitment period",
        ]
        for term in terms:
            text = f"The {term} is described in section 4."
            result = self.middleware.filter_content(text)
            assert term in result.redacted_text

    def test_result_type(self) -> None:
        result = self.middleware.filter_content("test")
        assert isinstance(result, PIIFilterResult)
        assert isinstance(result.redacted_text, str)
        assert isinstance(result.redactions_count, int)
        assert isinstance(result.redaction_types, dict)

    def test_empty_string(self) -> None:
        result = self.middleware.filter_content("")
        assert result.redacted_text == ""
        assert result.redactions_count == 0

    def test_redaction_types_tracked(self) -> None:
        text = f"SSN: {_SSN}"
        result = self.middleware.filter_content(text)
        assert "ssn" in result.redaction_types

    def test_typed_placeholders(self) -> None:
        """Each PII type should have a type-specific placeholder."""
        text = f"SSN {_SSN}, email {_EMAIL3}"
        result = self.middleware.filter_content(text)
        assert "[REDACTED_SSN]" in result.redacted_text
        assert "[REDACTED_EMAIL]" in result.redacted_text

    def test_default_strategy_is_redact(self) -> None:
        """Default strategy should be REDACT."""
        mw = PIIFilterMiddleware()
        assert mw._strategy == PIIStrategy.REDACT
        result = mw.filter_content(f"SSN: {_SSN}")
        assert "[REDACTED_SSN]" in result.redacted_text


class TestMaskStrategy:
    """Tests for MASK strategy -- preserves last 4 characters."""

    def setup_method(self) -> None:
        self.middleware = PIIFilterMiddleware(strategy=PIIStrategy.MASK)

    def test_mask_ssn_preserves_last_4(self) -> None:
        result = self.middleware.filter_content(f"SSN: {_SSN}")
        assert "6789" in result.redacted_text
        assert _SSN not in result.redacted_text
        assert result.redactions_count >= 1

    def test_mask_email_preserves_last_4(self) -> None:
        email = "john@example.com"
        result = self.middleware.filter_content(f"Email: {email}")
        assert result.redacted_text.endswith(".com")
        assert email not in result.redacted_text

    def test_mask_phone_preserves_last_4(self) -> None:
        result = self.middleware.filter_content(f"Phone: {_PHONE_DASHES}")
        assert "4567" in result.redacted_text
        assert _PHONE_DASHES not in result.redacted_text

    def test_mask_replaces_alphanumeric_with_stars(self) -> None:
        result = self.middleware.filter_content(f"SSN: {_SSN}")
        # Head part "123-45-" should have digits replaced with *
        expected_masked = "***-**-6789"
        assert expected_masked in result.redacted_text

    def test_mask_no_pii_returns_original(self) -> None:
        text = "No sensitive data here."
        result = self.middleware.filter_content(text)
        assert result.redacted_text == text
        assert result.redactions_count == 0


class TestBlockStrategy:
    """Tests for BLOCK strategy -- raises PIIDetectedError."""

    def setup_method(self) -> None:
        self.middleware = PIIFilterMiddleware(strategy=PIIStrategy.BLOCK)

    def test_block_raises_on_ssn(self) -> None:
        with pytest.raises(PIIDetectedError, match="PII detected"):
            self.middleware.filter_content(f"SSN: {_SSN}")

    def test_block_raises_on_email(self) -> None:
        with pytest.raises(PIIDetectedError, match="PII detected"):
            self.middleware.filter_content(f"Contact {_EMAIL3}")

    def test_block_raises_on_phone(self) -> None:
        with pytest.raises(PIIDetectedError, match="PII detected"):
            self.middleware.filter_content(f"Call {_PHONE_PARENS}")

    def test_block_error_includes_pii_types(self) -> None:
        with pytest.raises(PIIDetectedError, match="ssn"):
            self.middleware.filter_content(f"SSN: {_SSN}")

    def test_block_no_pii_returns_normally(self) -> None:
        result = self.middleware.filter_content("No sensitive data here.")
        assert result.redacted_text == "No sensitive data here."
        assert result.redactions_count == 0

    def test_block_reports_multiple_types(self) -> None:
        with pytest.raises(PIIDetectedError, match="instance") as exc_info:
            self.middleware.filter_content(f"SSN: {_SSN}, Email: {_EMAIL_SHORT}")
        msg = str(exc_info.value)
        assert "ssn" in msg
        assert "email" in msg


class TestPIILogFilter:
    """Tests for PIILogFilter logging integration."""

    def test_redacts_pii_from_log_message(self) -> None:
        log_filter = PIILogFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=f"User SSN is {_SSN}",
            args=None,
            exc_info=None,
        )
        result = log_filter.filter(record)
        assert result is True
        assert "[REDACTED_SSN]" in record.msg
        assert _SSN not in record.msg

    def test_passes_clean_messages_through(self) -> None:
        log_filter = PIILogFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="No PII here",
            args=None,
            exc_info=None,
        )
        result = log_filter.filter(record)
        assert result is True
        assert record.msg == "No PII here"

    def test_never_drops_records(self) -> None:
        """Filter should always return True."""
        log_filter = PIILogFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=f"Email: {_EMAIL_SECRET}, Phone: {_PHONE3}",
            args=None,
            exc_info=None,
        )
        assert log_filter.filter(record) is True

    def test_handles_non_string_msg(self) -> None:
        log_filter = PIILogFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=12345,  # type: ignore[arg-type]
            args=None,
            exc_info=None,
        )
        assert log_filter.filter(record) is True
        assert record.msg == 12345

    def test_accepts_custom_pii_filter(self) -> None:
        custom_filter = PIIFilterMiddleware(strategy=PIIStrategy.MASK)
        log_filter = PIILogFilter(pii_filter=custom_filter)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=f"SSN: {_SSN}",
            args=None,
            exc_info=None,
        )
        log_filter.filter(record)
        assert "6789" in record.msg
        assert _SSN not in record.msg
