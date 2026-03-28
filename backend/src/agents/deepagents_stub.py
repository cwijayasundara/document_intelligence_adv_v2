"""Stub implementation of the DeepAgents SDK interface.

Provides the same API surface as deepagents>=0.4.12 so the orchestrator
can be developed and tested without the real package installed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Middleware:
    """Base middleware stub."""

    name: str = ""


class FilesystemMiddleware(Middleware):
    """Middleware for filesystem access."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(name="filesystem")
        self.config = kwargs


class SubAgentMiddleware(Middleware):
    """Middleware for subagent dispatch."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(name="subagent")
        self.config = kwargs


class SummarizationMiddleware(Middleware):
    """Middleware for context summarization."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(name="summarization")
        self.config = kwargs


@dataclass
class SubAgentSlot:
    """A named slot for a subagent in the registry."""

    name: str
    agent: DeepAgent | None = None
    description: str = ""


@dataclass
class DeepAgent:
    """Stub DeepAgent that mimics the real SDK interface."""

    model: str = ""
    middleware: list[Middleware] = field(default_factory=list)
    subagents: dict[str, SubAgentSlot] = field(default_factory=dict)
    tools: list[Any] = field(default_factory=list)

    async def run(self, prompt: str) -> dict[str, Any]:
        """Run the agent with a prompt. Returns a stub response."""
        return {
            "status": "ok",
            "response": f"Stub response for: {prompt}",
            "model": self.model,
        }

    async def health_check(self) -> dict[str, str]:
        """Check agent health."""
        return {"status": "healthy", "model": self.model}


def create_deep_agent(
    model: str,
    middleware: list[Middleware] | None = None,
    subagents: dict[str, SubAgentSlot] | None = None,
    tools: list[Any] | None = None,
) -> DeepAgent:
    """Factory function to create a configured DeepAgent.

    Args:
        model: Model identifier (e.g. "openai:gpt-5.4-mini").
        middleware: List of middleware instances.
        subagents: Named subagent slots.
        tools: Agent tool definitions.

    Returns:
        A configured DeepAgent instance.
    """
    return DeepAgent(
        model=model,
        middleware=middleware or [],
        subagents=subagents or {},
        tools=tools or [],
    )
