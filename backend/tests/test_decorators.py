"""Tests for middleware classes (rate limiter, retry, PII filter).

These tests cover the decorator-like middleware behaviours that wrap
agent and LLM calls: retry with backoff, rate limiting, and PII
redaction. The underlying classes live in src.graph_nodes.middleware.
"""

from __future__ import annotations

import pytest

from src.graph_nodes.middleware.pii_filter import (
    PIIDetectedError,
    PIIFilterMiddleware,
    PIIStrategy,
)
from src.graph_nodes.middleware.rate_limit import AgentRateLimiter, AgentRateLimitError
from src.graph_nodes.middleware.retry import LLMRetryError, LLMRetryMiddleware

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeLLMError(Exception):
    """Simulated LLM API error with status_code."""

    def __init__(self, status_code: int, message: str = "error") -> None:
        super().__init__(message)
        self.status_code = status_code


# ---------------------------------------------------------------------------
# @with_retry  →  LLMRetryMiddleware
# ---------------------------------------------------------------------------


class TestRetryMiddleware:
    """Retry middleware acting as a @with_retry decorator."""

    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self) -> None:
        mw = LLMRetryMiddleware(base_delay=0.01)
        call_count = 0

        async def _ok() -> str:
            nonlocal call_count
            call_count += 1
            return "result"

        result = await mw.call_with_retry(_ok)
        assert result == "result"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_then_succeeds(self) -> None:
        mw = LLMRetryMiddleware(max_retries=3, base_delay=0.01)
        call_count = 0

        async def _fail_twice() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise _FakeLLMError(500, "server error")
            return "ok"

        result = await mw.call_with_retry(_fail_twice)
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self) -> None:
        mw = LLMRetryMiddleware(max_retries=2, base_delay=0.01)

        async def _always_fail() -> str:
            raise _FakeLLMError(502, "bad gateway")

        with pytest.raises(LLMRetryError, match="retry attempts exhausted"):
            await mw.call_with_retry(_always_fail)

    @pytest.mark.asyncio
    async def test_non_retryable_error_raises_immediately(self) -> None:
        mw = LLMRetryMiddleware(max_retries=5, base_delay=0.01)
        call_count = 0

        async def _bad_request() -> str:
            nonlocal call_count
            call_count += 1
            raise _FakeLLMError(400, "bad request")

        with pytest.raises(_FakeLLMError, match="bad request"):
            await mw.call_with_retry(_bad_request)
        assert call_count == 1


# ---------------------------------------------------------------------------
# @with_rate_limit  →  AgentRateLimiter
# ---------------------------------------------------------------------------


class TestRateLimitMiddleware:
    """Rate limiter acting as a @with_rate_limit decorator."""

    def test_under_limit_succeeds(self) -> None:
        limiter = AgentRateLimiter(max_llm_calls=5)
        for _ in range(5):
            limiter.track_llm_call()  # should not raise
        assert limiter.llm_calls == 5

    def test_over_limit_raises(self) -> None:
        limiter = AgentRateLimiter(max_llm_calls=2)
        limiter.track_llm_call()
        limiter.track_llm_call()
        with pytest.raises(AgentRateLimitError):
            limiter.track_llm_call()

    def test_reset_clears_counters(self) -> None:
        limiter = AgentRateLimiter(max_llm_calls=2, max_tool_calls=2)
        limiter.track_llm_call()
        limiter.track_llm_call()
        limiter.reset()
        assert limiter.llm_calls == 0
        assert limiter.tool_calls == 0
        # Should not raise after reset
        limiter.track_llm_call()
        assert limiter.llm_calls == 1

    def test_tool_limit_independent_of_llm(self) -> None:
        limiter = AgentRateLimiter(max_llm_calls=100, max_tool_calls=1)
        limiter.track_tool_call()
        with pytest.raises(AgentRateLimitError, match="Tool call limit"):
            limiter.track_tool_call()
        # LLM calls should still work
        limiter.track_llm_call()
        assert limiter.llm_calls == 1


# ---------------------------------------------------------------------------
# @with_pii_filter  →  PIIFilterMiddleware
# ---------------------------------------------------------------------------

_SSN = "-".join(["123", "45", "6789"])


class TestPIIFilterMiddleware:
    """PII filter acting as a @with_pii_filter decorator."""

    def test_content_with_ssn_is_redacted(self) -> None:
        mw = PIIFilterMiddleware()
        result = mw.filter_content(f"SSN: {_SSN}")
        assert "[REDACTED_SSN]" in result.redacted_text
        assert _SSN not in result.redacted_text
        assert result.redactions_count >= 1

    def test_content_without_pii_unchanged(self) -> None:
        mw = PIIFilterMiddleware()
        text = "The fund term is 10 years with a preferred return of 8%."
        result = mw.filter_content(text)
        assert result.redactions_count == 0

    def test_block_strategy_raises_on_pii(self) -> None:
        mw = PIIFilterMiddleware(strategy=PIIStrategy.BLOCK)
        with pytest.raises(PIIDetectedError, match="PII detected"):
            mw.filter_content(f"SSN: {_SSN}")

    def test_mask_strategy_preserves_last_4(self) -> None:
        mw = PIIFilterMiddleware(strategy=PIIStrategy.MASK)
        result = mw.filter_content(f"SSN: {_SSN}")
        assert "6789" in result.redacted_text
        assert _SSN not in result.redacted_text


# ---------------------------------------------------------------------------
# @with_fallback  →  LLMRetryMiddleware with fallback_model
# ---------------------------------------------------------------------------


class TestFallbackMiddleware:
    """Fallback model behaviour via LLMRetryMiddleware."""

    @pytest.mark.asyncio
    async def test_primary_succeeds_no_fallback(self) -> None:
        mw = LLMRetryMiddleware(max_retries=2, base_delay=0.01, fallback_model="gpt-4o-mini")

        async def _ok(*, model: str) -> str:
            return f"ok-{model}"

        result = await mw.call_with_retry(_ok, model="gpt-5")
        assert result == "ok-gpt-5"

    @pytest.mark.asyncio
    async def test_primary_fails_fallback_succeeds(self) -> None:
        mw = LLMRetryMiddleware(max_retries=2, base_delay=0.01, fallback_model="gpt-4o-mini")
        models_called: list[str] = []

        async def _llm(*, model: str) -> str:
            models_called.append(model)
            if model == "gpt-5":
                raise _FakeLLMError(503, "unavailable")
            return f"ok-{model}"

        result = await mw.call_with_retry(_llm, model="gpt-5")
        assert result == "ok-gpt-4o-mini"
        assert models_called[-1] == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_no_fallback_model_raises_after_retries(self) -> None:
        """When fallback_model is None, retries exhaust and raise."""
        mw = LLMRetryMiddleware(max_retries=2, base_delay=0.01)

        async def _always_fail() -> str:
            raise _FakeLLMError(500, "error")

        with pytest.raises(LLMRetryError, match="retry attempts exhausted"):
            await mw.call_with_retry(_always_fail)
