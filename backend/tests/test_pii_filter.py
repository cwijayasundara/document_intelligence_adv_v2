"""Tests for PII filtering middleware."""

from src.agents.middleware.pii_filter import PIIFilterMiddleware, PIIFilterResult


class TestPIIFilterMiddleware:
    """Tests for PIIFilterMiddleware.filter_content."""

    def setup_method(self) -> None:
        self.middleware = PIIFilterMiddleware()

    def test_redacts_ssn(self) -> None:
        text = "SSN: 123-45-6789"
        result = self.middleware.filter_content(text)
        assert "[REDACTED_SSN]" in result.redacted_text
        assert "123-45-6789" not in result.redacted_text
        assert result.redactions_count >= 1

    def test_redacts_phone_with_parens(self) -> None:
        text = "Call (555) 123-4567 for info"
        result = self.middleware.filter_content(text)
        assert "[REDACTED_PHONE]" in result.redacted_text
        assert "(555) 123-4567" not in result.redacted_text

    def test_redacts_phone_dashes(self) -> None:
        text = "Phone: 555-123-4567"
        result = self.middleware.filter_content(text)
        assert "[REDACTED_PHONE]" in result.redacted_text
        assert "555-123-4567" not in result.redacted_text

    def test_redacts_email(self) -> None:
        text = "Contact john.doe@example.com for details"
        result = self.middleware.filter_content(text)
        assert "[REDACTED_EMAIL]" in result.redacted_text
        assert "john.doe@example.com" not in result.redacted_text

    def test_redacts_address(self) -> None:
        text = "Located at 123 Main Street in the city"
        result = self.middleware.filter_content(text)
        assert "[REDACTED_ADDRESS]" in result.redacted_text
        assert "123 Main Street" not in result.redacted_text

    def test_redacts_address_avenue(self) -> None:
        text = "Office at 456 Park Avenue"
        result = self.middleware.filter_content(text)
        assert "[REDACTED_ADDRESS]" in result.redacted_text

    def test_redacts_bank_account(self) -> None:
        text = "Account number: 12345678901234"
        result = self.middleware.filter_content(text)
        assert "[REDACTED_ACCOUNT]" in result.redacted_text
        assert "12345678901234" not in result.redacted_text

    def test_multiple_pii_types(self) -> None:
        text = "SSN: 123-45-6789, Email: test@example.com, Phone: (555) 234-5678"
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
        text = "SSN: 123-45-6789"
        result = self.middleware.filter_content(text)
        assert "ssn" in result.redaction_types

    def test_typed_placeholders(self) -> None:
        """Each PII type should have a type-specific placeholder."""
        text = "SSN 123-45-6789, email user@test.com"
        result = self.middleware.filter_content(text)
        assert "[REDACTED_SSN]" in result.redacted_text
        assert "[REDACTED_EMAIL]" in result.redacted_text
