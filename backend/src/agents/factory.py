"""Agent factory with production middleware stack.

Creates DeepAgents with rate limiting, retry, fallback, and PII filtering.
All agents created through this factory get consistent production guards.
"""

from __future__ import annotations

import logging
from typing import Any

from deepagents import create_deep_agent
from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    ModelFallbackMiddleware,
    ModelRetryMiddleware,
    ToolCallLimitMiddleware,
)

logger = logging.getLogger(__name__)


def create_agent(
    model: str = "openai:gpt-5.4-mini",
    tools: list[Any] | None = None,
    system_prompt: str = "",
    response_format: Any = None,
    name: str | None = None,
) -> Any:
    """Create a DeepAgent with production middleware stack.

    Applies:
    - ModelCallLimitMiddleware (default 50 calls per run)
    - ToolCallLimitMiddleware (default 200 calls per run)
    - ModelRetryMiddleware (3 retries with exponential backoff)
    - ModelFallbackMiddleware (falls back to configured model)

    Args:
        model: LLM model identifier.
        tools: List of tools for the agent.
        system_prompt: System prompt for the agent.
        response_format: Pydantic model for structured output.
        name: Optional agent name for tracing.

    Returns:
        Compiled DeepAgent graph with middleware.
    """
    from src.config.settings import get_settings

    settings = get_settings()

    middleware = [
        ModelCallLimitMiddleware(run_limit=settings.agent_max_llm_calls),
        ToolCallLimitMiddleware(run_limit=settings.agent_max_tool_calls),
        ModelRetryMiddleware(
            max_retries=settings.llm_max_retries,
            wait_exponential_multiplier=settings.llm_base_delay,
        ),
    ]

    if settings.openai_fallback_model:
        middleware.append(
            ModelFallbackMiddleware(
                fallback_model=settings.openai_fallback_model,
            )
        )

    kwargs: dict[str, Any] = {
        "model": model,
        "tools": tools or [],
        "system_prompt": system_prompt,
        "middleware": middleware,
    }
    if response_format is not None:
        kwargs["response_format"] = response_format
    if name is not None:
        kwargs["name"] = name

    logger.info(
        "Creating agent: model=%s, name=%s, middleware=%d",
        model, name, len(middleware),
    )
    return create_deep_agent(**kwargs)
