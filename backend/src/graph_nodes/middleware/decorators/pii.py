"""PII filtering decorator for agent functions."""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, ParamSpec, TypeVar

from src.graph_nodes.middleware.pii_filter import PIIFilterMiddleware, PIIStrategy

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def with_pii_filter(
    fn: Callable[P, T] | None = None,
    *,
    strategy: str = "redact",
    content_params: tuple[str, ...] = ("content", "parsed_content"),
) -> Callable[P, T]:
    """Filter PII from string arguments before calling the wrapped function.

    Intercepts keyword arguments matching `content_params` and applies
    PII redaction. Preserves PE financial terms.

    Can be used as @with_pii_filter or @with_pii_filter(strategy="mask").
    """
    pii_strategy = PIIStrategy(strategy)
    pii_filter = PIIFilterMiddleware(strategy=pii_strategy)

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            for param in content_params:
                if param in kwargs and isinstance(kwargs[param], str):
                    result = pii_filter.filter_content(kwargs[param])
                    kwargs[param] = result.redacted_text
                    if result.redactions_count > 0:
                        logger.debug(
                            "PII filtered %d items from '%s' param",
                            result.redactions_count,
                            param,
                        )
            return await func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    if fn is not None:
        return decorator(fn)
    return decorator  # type: ignore[return-value]
