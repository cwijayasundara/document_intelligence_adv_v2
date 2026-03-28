"""DeepAgent orchestrator with singleton factory access.

Creates the main orchestrator agent with subagent slots for:
classifier, extractor, judge, summarizer, rag_retriever.
"""

import asyncio

from src.agents.deepagents_stub import (
    DeepAgent,
    FilesystemMiddleware,
    SubAgentMiddleware,
    SubAgentSlot,
    SummarizationMiddleware,
    create_deep_agent,
)

# Singleton state
_orchestrator: DeepAgent | None = None
_lock: asyncio.Lock | None = None

SUBAGENT_NAMES = [
    "classifier",
    "extractor",
    "judge",
    "summarizer",
    "rag_retriever",
]


def _get_lock() -> asyncio.Lock:
    """Lazy-init the async lock (must be created inside a running loop)."""
    global _lock
    if _lock is None:
        _lock = asyncio.Lock()
    return _lock


def _build_orchestrator() -> DeepAgent:
    """Build a fresh orchestrator instance with configured middleware."""
    middleware = [
        FilesystemMiddleware(),
        SubAgentMiddleware(),
        SummarizationMiddleware(),
    ]

    subagents = {
        name: SubAgentSlot(name=name, description=f"{name} subagent (stub)")
        for name in SUBAGENT_NAMES
    }

    return create_deep_agent(
        model="openai:gpt-5.4-mini",
        middleware=middleware,
        subagents=subagents,
    )


async def get_orchestrator() -> DeepAgent:
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
