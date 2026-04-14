"""Tests for agent-level rate limiting."""

from __future__ import annotations

import pytest

from src.graph_nodes.middleware.rate_limit import AgentRateLimiter, AgentRateLimitError


class TestAgentRateLimiterLLMCalls:
    """Tests for LLM call tracking and limiting."""

    def test_llm_calls_within_limit_do_not_raise(self) -> None:
        limiter = AgentRateLimiter(max_llm_calls=5)
        for _ in range(5):
            limiter.track_llm_call()
        assert limiter.llm_calls == 5

    def test_exceeding_llm_limit_raises(self) -> None:
        limiter = AgentRateLimiter(max_llm_calls=3)
        for _ in range(3):
            limiter.track_llm_call()
        with pytest.raises(AgentRateLimitError, match="LLM call limit.*3.*exceeded.*4"):
            limiter.track_llm_call()


class TestAgentRateLimiterToolCalls:
    """Tests for tool call tracking and limiting."""

    def test_tool_calls_within_limit_do_not_raise(self) -> None:
        limiter = AgentRateLimiter(max_tool_calls=10)
        for _ in range(10):
            limiter.track_tool_call()
        assert limiter.tool_calls == 10

    def test_exceeding_tool_limit_raises(self) -> None:
        limiter = AgentRateLimiter(max_tool_calls=2)
        for _ in range(2):
            limiter.track_tool_call()
        with pytest.raises(AgentRateLimitError, match="Tool call limit.*2.*exceeded.*3"):
            limiter.track_tool_call()


class TestAgentRateLimiterReset:
    """Tests for the reset method."""

    def test_reset_clears_counters(self) -> None:
        limiter = AgentRateLimiter(max_llm_calls=5, max_tool_calls=5)
        for _ in range(3):
            limiter.track_llm_call()
            limiter.track_tool_call()
        limiter.reset()
        assert limiter.llm_calls == 0
        assert limiter.tool_calls == 0

    def test_reset_allows_new_calls(self) -> None:
        limiter = AgentRateLimiter(max_llm_calls=2, max_tool_calls=2)
        for _ in range(2):
            limiter.track_llm_call()
        limiter.reset()
        # Should not raise after reset
        limiter.track_llm_call()
        assert limiter.llm_calls == 1


class TestAgentRateLimiterProperties:
    """Tests for property accessors."""

    def test_properties_return_correct_values(self) -> None:
        limiter = AgentRateLimiter(max_llm_calls=10, max_tool_calls=20)
        assert limiter.max_llm_calls == 10
        assert limiter.max_tool_calls == 20
        assert limiter.llm_calls == 0
        assert limiter.tool_calls == 0

    def test_default_limits(self) -> None:
        limiter = AgentRateLimiter()
        assert limiter.max_llm_calls == 50
        assert limiter.max_tool_calls == 200

    def test_custom_limits(self) -> None:
        limiter = AgentRateLimiter(max_llm_calls=100, max_tool_calls=500)
        assert limiter.max_llm_calls == 100
        assert limiter.max_tool_calls == 500
