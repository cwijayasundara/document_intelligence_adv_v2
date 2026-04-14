"""Fallback model decorator for agent functions."""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, ParamSpec, TypeVar

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def with_fallback(
    fn: Callable[P, T] | None = None,
    *,
    fallback_model: str = "",
) -> Callable[P, T]:
    """Try the wrapped function; on failure, retry with a fallback model.

    The wrapped function must accept a `model` keyword argument.
    If `fallback_model` is empty, this decorator is a no-op.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        if not fallback_model:
            return func

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                logger.info(
                    "Primary model failed for %s, falling back to %s: %s",
                    func.__name__,
                    fallback_model,
                    exc,
                )
                kwargs["model"] = fallback_model
                return await func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    if fn is not None:
        return decorator(fn)
    return decorator  # type: ignore[return-value]
