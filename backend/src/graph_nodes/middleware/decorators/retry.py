"""Retry decorator with exponential backoff for agent functions."""

from __future__ import annotations

import asyncio
import functools
import logging
import random
from typing import Any, Callable, ParamSpec, TypeVar

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")

RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503, 504})


def with_retry(
    fn: Callable[P, T] | None = None,
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_codes: frozenset[int] = RETRYABLE_STATUS_CODES,
) -> Callable[P, T]:
    """Retry async function on transient failures with exponential backoff.

    Retries on rate limits (429) and server errors (5xx).
    Non-retryable errors (400, 422) are raised immediately.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
                    if status_code and status_code not in retryable_codes:
                        raise

                    last_exc = exc
                    if attempt < max_retries:
                        delay = min(
                            base_delay * (2**attempt) + random.uniform(0, 0.5),
                            max_delay,
                        )
                        logger.warning(
                            "Agent call failed (attempt %d/%d): %s. Retrying in %.1fs...",
                            attempt + 1,
                            max_retries,
                            exc,
                            delay,
                        )
                        await asyncio.sleep(delay)

            raise last_exc  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    if fn is not None:
        return decorator(fn)
    return decorator  # type: ignore[return-value]
