"""DeepAgent orchestrator with singleton factory access.

Creates the main orchestrator agent with subagent slots for:
classifier, extractor, judge, summarizer, rag_retriever.
"""

from __future__ import annotations

import asyncio
from typing import Any

from deepagents import (
    SubAgent,
    SubAgentMiddleware,
    create_deep_agent,
)
from deepagents.middleware.summarization import SummarizationMiddleware

from src.agents.backends import InMemoryBackend

# Singleton state
_orchestrator: Any | None = None
_lock: asyncio.Lock | None = None

SUBAGENT_NAMES = [
    "classifier",
    "extractor",
    "judge",
    "summarizer",
    "rag_retriever",
]

SUBAGENT_DESCRIPTIONS = {
    "classifier": "Classifies documents into user-defined categories",
    "extractor": "Extracts structured fields from documents",
    "judge": "Evaluates extraction confidence per field",
    "summarizer": "Generates document summaries with key topics",
    "rag_retriever": "Retrieves relevant document chunks via hybrid search",
}


def _get_lock() -> asyncio.Lock:
    """Lazy-init the async lock (must be created inside a running loop)."""
    global _lock
    if _lock is None:
        _lock = asyncio.Lock()
    return _lock


def _build_orchestrator() -> Any:
    """Build a fresh orchestrator instance with configured middleware."""
    backend = InMemoryBackend()

    subagents: list[SubAgent] = [
        SubAgent(
            name=name,
            description=SUBAGENT_DESCRIPTIONS.get(name, f"{name} subagent"),
            system_prompt=f"You are the {name} subagent for a document intelligence system.",
            tools=[],
            model="openai:gpt-5.4-mini",
        )
        for name in SUBAGENT_NAMES
    ]

    middleware = [
        SubAgentMiddleware(backend=backend, subagents=subagents),
        SummarizationMiddleware(model="openai:gpt-5.4-mini", backend=backend),
    ]

    return create_deep_agent(
        model="openai:gpt-5.4-mini",
        middleware=middleware,
        subagents=subagents,
        backend=backend,
    )


async def get_orchestrator() -> Any:
    """Get or create the singleton orchestrator instance.

    Thread-safe via asyncio.Lock.

    Returns:
        The singleton DeepAgent orchestrator.
    """
    global _orchestrator
    lock = _get_lock()

    async with lock:
        if _orchestrator is None:
            _orchestrator = _build_orchestrator()
        return _orchestrator


async def reset_orchestrator() -> None:
    """Reset the singleton (for testing)."""
    global _orchestrator
    lock = _get_lock()
    async with lock:
        _orchestrator = None
