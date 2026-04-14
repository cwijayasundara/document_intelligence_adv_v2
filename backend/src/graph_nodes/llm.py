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
) -> BaseChatModel:
    """Create or return a cached LLM instance.

    Args:
        model: Model identifier (e.g. "gpt-5.4-mini").
               If None, uses settings.openai_model.
        temperature: Sampling temperature (default 0).

    Returns:
        A BaseChatModel instance.
    """
    if model is None:
        from src.config.settings import get_settings

        model = get_settings().openai_model

    logger.debug("Creating LLM: model=%s, temperature=%s", model, temperature)

    return init_chat_model(
        model=model,
        temperature=temperature,
    )
