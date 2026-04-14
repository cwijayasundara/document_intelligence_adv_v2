"""Context window management decorator for agent functions."""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, ParamSpec, TypeVar

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def with_context_window(
    fn: Callable[P, T] | None = None,
    *,
    max_chars: int = 400_000,
    content_params: tuple[str, ...] = ("content", "parsed_content"),
) -> Callable[P, T]:
    """Truncate oversized content to fit within the model's context window.

    Uses a character-based estimate (1 token ~ 4 chars). If content exceeds
    `max_chars`, it is truncated with a notice appended.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            for param in content_params:
                if param in kwargs and isinstance(kwargs[param], str):
                    text = kwargs[param]
                    if len(text) > max_chars:
                        original_len = len(text)
                        kwargs[param] = (
                            text[:max_chars]
                            + f"\n\n[TRUNCATED: {original_len} chars "
                            + f"→ {max_chars} chars]"
                        )
                        logger.info(
                            "Truncated '%s' from %d to %d chars for %s",
                            param,
                            original_len,
                            max_chars,
                            func.__name__,
                        )
            return await func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    if fn is not None:
        return decorator(fn)
    return decorator  # type: ignore[return-value]
