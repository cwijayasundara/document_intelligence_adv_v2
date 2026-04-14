"""Rate limiting decorator for agent functions using contextvars."""

from __future__ import annotations

import contextvars
import functools
import logging
from typing import Any, Callable, ParamSpec, TypeVar

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")

_call_count: contextvars.ContextVar[dict[str, int]] = contextvars.ContextVar(
    "agent_call_count", default={}
)


class RateLimitExceeded(Exception):
    """Raised when an agent function exceeds its call limit."""


def reset_rate_limits() -> None:
    """Reset all rate limit counters (call at pipeline run start)."""
    _call_count.set({})


def with_rate_limit(
    fn: Callable[P, T] | None = None,
    *,
    max_calls: int = 50,
    scope: str = "default",
) -> Callable[P, T]:
    """Track and limit calls per pipeline run via contextvars.

    Each pipeline run should set a fresh context to reset counters.
    The `scope` key isolates limits for different agent functions.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            counts = dict(_call_count.get())  # copy to avoid shared mutation
            key = f"{scope}:{func.__name__}"
            current = counts.get(key, 0) + 1
            if current > max_calls:
                raise RateLimitExceeded(
                    f"Agent {func.__name__} exceeded call limit "
                    f"({max_calls}): {current} calls"
                )
            counts[key] = current
            _call_count.set(counts)
            return await func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    if fn is not None:
        return decorator(fn)
    return decorator  # type: ignore[return-value]
