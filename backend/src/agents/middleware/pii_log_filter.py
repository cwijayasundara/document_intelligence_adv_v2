"""PII-safe logging filter that redacts sensitive data from log messages."""

from __future__ import annotations

import logging

from src.agents.middleware.pii_filter import PIIFilterMiddleware


class PIILogFilter(logging.Filter):
    """Logging filter that redacts PII from log record messages."""

    def __init__(self, name: str = "", pii_filter: PIIFilterMiddleware | None = None) -> None:
        super().__init__(name)
        self._pii = pii_filter or PIIFilterMiddleware()

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact PII from log message. Always returns True (never drops records)."""
        if isinstance(record.msg, str):
            result = self._pii.filter_content(record.msg)
            record.msg = result.redacted_text
        return True
