"""Tests for the DeepAgent orchestrator."""

from unittest.mock import MagicMock, patch

from src.agents.orchestrator import (
    SUBAGENT_NAMES,
    _build_orchestrator,
    get_orchestrator,
    reset_orchestrator,
)


@patch("src.agents.orchestrator.SummarizationMiddleware", MagicMock)
@patch("src.agents.orchestrator.SubAgentMiddleware", MagicMock)
@patch("src.agents.orchestrator.create_deep_agent")
def test_build_orchestrator_calls_create_deep_agent(mock_create: MagicMock) -> None:
    """_build_orchestrator calls create_deep_agent with correct args."""
    mock_agent = MagicMock()
    mock_create.return_value = mock_agent

    result = _build_orchestrator()

    assert result is mock_agent
    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args[1]
    assert call_kwargs["model"] == "openai:gpt-5.4-mini"
    assert len(call_kwargs["middleware"]) == 3
    assert len(call_kwargs["subagents"]) == 5


@patch("src.agents.orchestrator.SummarizationMiddleware", MagicMock)
@patch("src.agents.orchestrator.SubAgentMiddleware", MagicMock)
@patch("src.agents.orchestrator.create_deep_agent")
def test_orchestrator_subagent_names(mock_create: MagicMock) -> None:
    """Orchestrator passes all five subagent configs."""
    mock_create.return_value = MagicMock()
    _build_orchestrator()

    call_kwargs = mock_create.call_args[1]
    subagent_names = [s["name"] for s in call_kwargs["subagents"]]
    for name in SUBAGENT_NAMES:
        assert name in subagent_names


@patch("src.agents.orchestrator.SummarizationMiddleware", MagicMock)
@patch("src.agents.orchestrator.SubAgentMiddleware", MagicMock)
@patch("src.agents.orchestrator.create_deep_agent")
def test_orchestrator_subagents_are_dicts(mock_create: MagicMock) -> None:
    """Subagents are passed as list of dicts (not SubAgentSlot)."""
    mock_create.return_value = MagicMock()
    _build_orchestrator()

    call_kwargs = mock_create.call_args[1]
    for subagent in call_kwargs["subagents"]:
        assert isinstance(subagent, dict)
        assert "name" in subagent
        assert "description" in subagent
        assert "system_prompt" in subagent
        assert "tools" in subagent
        assert "model" in subagent


@patch("src.agents.orchestrator.SummarizationMiddleware", MagicMock)
@patch("src.agents.orchestrator.SubAgentMiddleware", MagicMock)
@patch("src.agents.orchestrator.create_deep_agent")
async def test_get_orchestrator_singleton(mock_create: MagicMock) -> None:
    """get_orchestrator returns the same instance on multiple calls."""
    mock_agent = MagicMock()
    mock_create.return_value = mock_agent

    await reset_orchestrator()
    agent1 = await get_orchestrator()
    agent2 = await get_orchestrator()
    assert agent1 is agent2


@patch("src.agents.orchestrator.SummarizationMiddleware", MagicMock)
@patch("src.agents.orchestrator.SubAgentMiddleware", MagicMock)
@patch("src.agents.orchestrator.create_deep_agent")
async def test_reset_orchestrator(mock_create: MagicMock) -> None:
    """reset_orchestrator clears the singleton."""
    mock_create.return_value = MagicMock()

    await reset_orchestrator()
    agent1 = await get_orchestrator()

    mock_create.return_value = MagicMock()
    await reset_orchestrator()
    agent2 = await get_orchestrator()

    assert agent1 is not agent2


@patch("src.agents.orchestrator.SummarizationMiddleware", MagicMock)
@patch("src.agents.orchestrator.SubAgentMiddleware", MagicMock)
@patch("src.agents.orchestrator.create_deep_agent")
def test_orchestrator_has_filesystem_backend(mock_create: MagicMock) -> None:
    """Orchestrator passes a FilesystemBackend."""
    mock_create.return_value = MagicMock()
    _build_orchestrator()

    call_kwargs = mock_create.call_args[1]
    assert "backend" in call_kwargs
    # The backend should be a FilesystemBackend instance
    assert call_kwargs["backend"] is not None
