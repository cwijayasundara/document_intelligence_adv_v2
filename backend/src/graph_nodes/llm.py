"""Shared LLM factory using LangChain's init_chat_model().

Provides a provider-agnostic way to create chat models with
structured output, tool binding, and built-in retry support.

Usage:
    from src.graph_nodes.llm import get_llm

    # Plain LLM
    llm = get_llm()
    result = await llm.ainvoke([SystemMessage(...), HumanMessage(...)])

    # With structured output
    structured = get_llm().with_structured_output(MyPydanticModel)
    result = await structured.ainvoke([...])

    # With tools
    llm_with_tools = get_llm().bind_tools([my_tool])
"""

from __future__ import annotations

import functools
import logging

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=8)
def get_llm(
    model: str | None = None,
    temperature: float = 0,
    timeout: float | None = None,
    max_retries: int | None = None,
) -> BaseChatModel:
    """Create or return a cached LLM instance.

    Args:
        model: Model identifier (e.g. "gpt-5.4-mini"). If None, uses
            settings.openai_model.
        temperature: Sampling temperature (default 0).
        timeout: Per-call timeout in seconds. Prevents a single upstream hiccup
            (e.g. OpenAI 502 with Retry-After: 60) from stalling a long batch.
            Defaults to settings.llm_timeout_seconds when not overridden.
        max_retries: Transient-error retry count. Defaults to
            settings.llm_max_retries.
    """
    from src.config.settings import get_settings

    settings = get_settings()
    if model is None:
        model = settings.openai_model
    if timeout is None:
        timeout = float(getattr(settings, "llm_timeout_seconds", 90.0))
    if max_retries is None:
        max_retries = int(settings.llm_max_retries)

    logger.debug(
        "Creating LLM: model=%s temperature=%s timeout=%s max_retries=%s",
        model, temperature, timeout, max_retries,
    )

    return init_chat_model(
        model=model,
        temperature=temperature,
        timeout=timeout,
        max_retries=max_retries,
    )
