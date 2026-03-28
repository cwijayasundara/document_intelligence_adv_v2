"""Tests for the DeepAgent orchestrator scaffold."""

from src.agents.deepagents_stub import (
    DeepAgent,
    FilesystemMiddleware,
    SubAgentSlot,
    create_deep_agent,
)
from src.agents.orchestrator import (
    SUBAGENT_NAMES,
    _build_orchestrator,
    get_orchestrator,
    reset_orchestrator,
)


async def test_build_orchestrator_returns_deep_agent() -> None:
    """_build_orchestrator creates a properly configured DeepAgent."""
    agent = _build_orchestrator()
    assert isinstance(agent, DeepAgent)
    assert agent.model == "openai:gpt-5.4-mini"


async def test_orchestrator_has_middleware() -> None:
    """Orchestrator has all three required middleware."""
    agent = _build_orchestrator()
    middleware_names = [m.name for m in agent.middleware]
    assert "filesystem" in middleware_names
    assert "subagent" in middleware_names
    assert "summarization" in middleware_names


async def test_orchestrator_has_five_subagent_slots() -> None:
    """Orchestrator has 5 named subagent slots."""
    agent = _build_orchestrator()
    assert len(agent.subagents) == 5
    for name in SUBAGENT_NAMES:
        assert name in agent.subagents
        assert isinstance(agent.subagents[name], SubAgentSlot)


async def test_get_orchestrator_singleton() -> None:
    """get_orchestrator returns the same instance on multiple calls."""
    await reset_orchestrator()
    agent1 = await get_orchestrator()
    agent2 = await get_orchestrator()
    assert agent1 is agent2


async def test_reset_orchestrator() -> None:
    """reset_orchestrator clears the singleton."""
    await reset_orchestrator()
    agent1 = await get_orchestrator()
    await reset_orchestrator()
    agent2 = await get_orchestrator()
    assert agent1 is not agent2


async def test_orchestrator_health_check() -> None:
    """Orchestrator responds to health check without error."""
    await reset_orchestrator()
    agent = await get_orchestrator()
    result = await agent.health_check()
    assert result["status"] == "healthy"
    assert result["model"] == "openai:gpt-5.4-mini"


async def test_orchestrator_run_stub() -> None:
    """Orchestrator run returns a stub response."""
    await reset_orchestrator()
    agent = await get_orchestrator()
    result = await agent.run("test prompt")
    assert result["status"] == "ok"
    assert "test prompt" in result["response"]


async def test_create_deep_agent_factory() -> None:
    """create_deep_agent factory function works correctly."""
    agent = create_deep_agent(
        model="test:model",
        middleware=[FilesystemMiddleware()],
        subagents={"test": SubAgentSlot(name="test")},
    )
    assert agent.model == "test:model"
    assert len(agent.middleware) == 1
    assert "test" in agent.subagents


async def test_subagent_slot_defaults() -> None:
    """SubAgentSlot has correct defaults."""
    slot = SubAgentSlot(name="classifier")
    assert slot.name == "classifier"
    assert slot.agent is None
    assert slot.description == ""
