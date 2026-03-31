"""LLM retry middleware with exponential backoff and model fallback."""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503, 504})


class LLMRetryError(Exception):
    """Raised when all retry attempts and fallback are exhausted."""


class LLMRetryMiddleware:
    """Wraps async LLM calls with exponential backoff and optional model fallback.

    Retries on rate limits (429), server errors (5xx).
    Non-retryable errors (400, 422) are raised immediately.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        fallback_model: str | None = None,
    ) -> None:
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._fallback_model = fallback_model

    async def call_with_retry(
        self,
        fn: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Call fn with exponential backoff.

        Falls back to alternate model on exhaustion.
        """
        last_exc: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                return await fn(*args, **kwargs)
            except Exception as exc:
                status_code = getattr(
                    exc,
                    "status_code",
                    None,
                ) or getattr(exc, "code", None)
                if status_code and status_code not in RETRYABLE_STATUS_CODES:
                    raise  # Non-retryable (400, 422, etc.)

                last_exc = exc
                delay = min(
                    self._base_delay * (2**attempt) + random.uniform(0, 0.5),
                    self._max_delay,
                )
                logger.warning(
                    "LLM call failed (attempt %d/%d): %s. Retrying in %.1fs...",
                    attempt + 1,
                    self._max_retries,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)

        # All retries exhausted -- try fallback model if configured
        if self._fallback_model and "model" in kwargs:
            logger.info(
                "Falling back to model: %s",
                self._fallback_model,
            )
            kwargs["model"] = self._fallback_model
            try:
                return await fn(*args, **kwargs)
            except Exception as exc:
                raise LLMRetryError(
                    f"Fallback model {self._fallback_model} also failed: {exc}"
                ) from exc

        raise LLMRetryError(
            f"All {self._max_retries} retry attempts exhausted",
        ) from last_exc

    @property
    def max_retries(self) -> int:
        """Return configured max retries."""
        return self._max_retries

    @property
    def fallback_model(self) -> str | None:
        """Return configured fallback model."""
        return self._fallback_model
