"""Telemetry decorator for agent function observability."""

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable, ParamSpec, TypeVar

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def with_telemetry(
    fn: Callable[P, T] | None = None,
    *,
    node_name: str = "",
) -> Callable[P, T]:
    """Emit timing and success/failure telemetry for agent function calls.

    Logs duration and result status. If the PipelineEventBus is available,
    publishes structured events for observability.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        label = node_name or func.__name__

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.monotonic()
            try:
                result = await func(*args, **kwargs)
                duration = time.monotonic() - start
                logger.info(
                    "[telemetry] %s completed in %.2fs",
                    label,
                    duration,
                )
                return result
            except Exception as exc:
                duration = time.monotonic() - start
                logger.error(
                    "[telemetry] %s failed after %.2fs: %s",
                    label,
                    duration,
                    exc,
                )
                raise

        return wrapper  # type: ignore[return-value]

    if fn is not None:
        return decorator(fn)
    return decorator  # type: ignore[return-value]
