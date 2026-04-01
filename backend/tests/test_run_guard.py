"""Tests for RunGuard double-texting prevention."""

from __future__ import annotations

import pytest

from src.api.middleware.run_guard import RunGuard


@pytest.fixture
def guard() -> RunGuard:
    """Create a fresh RunGuard for each test."""
    return RunGuard()


@pytest.mark.asyncio
async def test_acquire_returns_true_on_first_call(guard: RunGuard) -> None:
    """First acquire for a resource should succeed."""
    result = await guard.acquire("doc-1")
    assert result is True


@pytest.mark.asyncio
async def test_acquire_returns_false_on_second_call(guard: RunGuard) -> None:
    """Second acquire for the same resource should be rejected."""
    await guard.acquire("doc-1")
    result = await guard.acquire("doc-1")
    assert result is False


@pytest.mark.asyncio
async def test_release_allows_reacquisition(guard: RunGuard) -> None:
    """After release, the same resource can be acquired again."""
    await guard.acquire("doc-1")
    await guard.release("doc-1")
    result = await guard.acquire("doc-1")
    assert result is True


@pytest.mark.asyncio
async def test_different_resources_can_be_acquired_concurrently(guard: RunGuard) -> None:
    """Different resource IDs should not conflict."""
    result_a = await guard.acquire("doc-1")
    result_b = await guard.acquire("doc-2")
    assert result_a is True
    assert result_b is True


@pytest.mark.asyncio
async def test_active_count_property(guard: RunGuard) -> None:
    """active_count should reflect the number of held resources."""
    assert guard.active_count == 0
    await guard.acquire("doc-1")
    assert guard.active_count == 1
    await guard.acquire("doc-2")
    assert guard.active_count == 2
    await guard.release("doc-1")
    assert guard.active_count == 1
    await guard.release("doc-2")
    assert guard.active_count == 0


@pytest.mark.asyncio
async def test_release_nonexistent_resource_is_safe(guard: RunGuard) -> None:
    """Releasing a resource that was never acquired should not raise."""
    await guard.release("never-acquired")
    assert guard.active_count == 0
