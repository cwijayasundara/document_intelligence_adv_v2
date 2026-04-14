"""Tests for LLM retry middleware with exponential backoff and fallback."""

from __future__ import annotations

import pytest

from src.graph_nodes.middleware.retry import (
    LLMRetryError,
    LLMRetryMiddleware,
)


class _LLMError(Exception):
    """Simulated LLM API error with status_code attribute."""

    def __init__(self, status_code: int, message: str = "error") -> None:
        super().__init__(message)
        self.status_code = status_code


@pytest.mark.asyncio
async def test_successful_call_no_retry() -> None:
    """First attempt succeeds -- no retry needed."""
    middleware = LLMRetryMiddleware(base_delay=0.01)
    call_count = 0

    async def _ok() -> str:
        nonlocal call_count
        call_count += 1
        return "ok"

    result = await middleware.call_with_retry(_ok)
    assert result == "ok"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_on_429_succeeds() -> None:
    """429 rate-limit triggers retry; succeeds on second attempt."""
    middleware = LLMRetryMiddleware(max_retries=3, base_delay=0.01)
    call_count = 0

    async def _rate_limited() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise _LLMError(429, "rate limited")
        return "ok"

    result = await middleware.call_with_retry(_rate_limited)
    assert result == "ok"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_on_500_succeeds() -> None:
    """500 server error triggers retry; succeeds on second attempt."""
    middleware = LLMRetryMiddleware(max_retries=3, base_delay=0.01)
    call_count = 0

    async def _server_error() -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise _LLMError(500, "internal server error")
        return "ok"

    result = await middleware.call_with_retry(_server_error)
    assert result == "ok"
    assert call_count == 2


@pytest.mark.asyncio
async def test_non_retryable_error_raises_immediately() -> None:
    """400 bad request is not retried -- raises immediately."""
    middleware = LLMRetryMiddleware(max_retries=3, base_delay=0.01)
    call_count = 0

    async def _bad_request() -> str:
        nonlocal call_count
        call_count += 1
        raise _LLMError(400, "bad request")

    with pytest.raises(_LLMError, match="bad request"):
        await middleware.call_with_retry(_bad_request)
    assert call_count == 1


@pytest.mark.asyncio
async def test_fallback_model_used_after_retries_exhausted() -> None:
    """After max retries, fallback model is tried and succeeds."""
    middleware = LLMRetryMiddleware(
        max_retries=2,
        base_delay=0.01,
        fallback_model="gpt-4o-mini",
    )
    models_called: list[str] = []

    async def _llm_call(*, model: str) -> str:
        models_called.append(model)
        if model == "gpt-5.4-mini":
            raise _LLMError(503, "service unavailable")
        return "fallback-ok"

    result = await middleware.call_with_retry(
        _llm_call,
        model="gpt-5.4-mini",
    )
    assert result == "fallback-ok"
    # 2 retries with primary + 1 fallback call
    assert len(models_called) == 3
    assert models_called[-1] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_retry_error_when_all_exhausted() -> None:
    """LLMRetryError raised when retries + fallback all fail."""
    middleware = LLMRetryMiddleware(
        max_retries=2,
        base_delay=0.01,
        fallback_model="gpt-4o-mini",
    )

    async def _always_fail(*, model: str) -> str:
        raise _LLMError(502, f"bad gateway for {model}")

    with pytest.raises(LLMRetryError, match="Fallback model.*also failed"):
        await middleware.call_with_retry(
            _always_fail,
            model="gpt-5.4-mini",
        )


@pytest.mark.asyncio
async def test_retry_error_no_fallback() -> None:
    """LLMRetryError raised when retries exhausted and no fallback."""
    middleware = LLMRetryMiddleware(max_retries=2, base_delay=0.01)

    async def _always_fail() -> str:
        raise _LLMError(500, "server error")

    with pytest.raises(LLMRetryError, match="retry attempts exhausted"):
        await middleware.call_with_retry(_always_fail)


def test_properties() -> None:
    """max_retries and fallback_model properties return config."""
    mw = LLMRetryMiddleware(max_retries=5, fallback_model="gpt-4o")
    assert mw.max_retries == 5
    assert mw.fallback_model == "gpt-4o"

    mw_default = LLMRetryMiddleware()
    assert mw_default.max_retries == 3
    assert mw_default.fallback_model is None
