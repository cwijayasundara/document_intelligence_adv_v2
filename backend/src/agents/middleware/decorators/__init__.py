"""Composable middleware decorators for agent functions.

Usage:
    @with_pii_filter
    @with_retry(max_retries=3)
    @with_rate_limit(max_calls=50)
    @with_telemetry(node_name="classify")
    async def classify_document(content: str, ...) -> ClassificationResult:
        ...
"""

from src.agents.middleware.decorators.context_window import with_context_window
from src.agents.middleware.decorators.fallback import with_fallback
from src.agents.middleware.decorators.pii import with_pii_filter
from src.agents.middleware.decorators.rate_limit import (
    RateLimitExceeded,
    reset_rate_limits,
    with_rate_limit,
)
from src.agents.middleware.decorators.retry import with_retry
from src.agents.middleware.decorators.telemetry import with_telemetry

__all__ = [
    "RateLimitExceeded",
    "reset_rate_limits",
    "with_context_window",
    "with_fallback",
    "with_pii_filter",
    "with_rate_limit",
    "with_retry",
    "with_telemetry",
]
