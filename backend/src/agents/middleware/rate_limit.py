"""Agent-level rate limiting to prevent runaway loops."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class AgentRateLimitError(Exception):
    """Raised when an agent exceeds its call limit."""


class AgentRateLimiter:
    """Tracks and limits LLM and tool calls per pipeline run.

    Create one instance per run to enforce per-run limits.
    """

    def __init__(
        self,
        max_llm_calls: int = 50,
        max_tool_calls: int = 200,
    ) -> None:
        self._max_llm = max_llm_calls
        self._max_tool = max_tool_calls
        self._llm_count: int = 0
        self._tool_count: int = 0

    def track_llm_call(self) -> None:
        """Track an LLM call. Raises AgentRateLimitError if limit exceeded."""
        self._llm_count += 1
        if self._llm_count > self._max_llm:
            logger.warning("LLM call limit exceeded: %d/%d", self._llm_count, self._max_llm)
            raise AgentRateLimitError(
                f"LLM call limit ({self._max_llm}) exceeded: {self._llm_count} calls"
            )

    def track_tool_call(self) -> None:
        """Track a tool call. Raises AgentRateLimitError if limit exceeded."""
        self._tool_count += 1
        if self._tool_count > self._max_tool:
            logger.warning("Tool call limit exceeded: %d/%d", self._tool_count, self._max_tool)
            raise AgentRateLimitError(
                f"Tool call limit ({self._max_tool}) exceeded: {self._tool_count} calls"
            )

    def reset(self) -> None:
        """Reset all counters."""
        self._llm_count = 0
        self._tool_count = 0

    @property
    def llm_calls(self) -> int:
        return self._llm_count

    @property
    def tool_calls(self) -> int:
        return self._tool_count

    @property
    def max_llm_calls(self) -> int:
        return self._max_llm

    @property
    def max_tool_calls(self) -> int:
        return self._max_tool
