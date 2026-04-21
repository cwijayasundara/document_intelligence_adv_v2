"""End-to-end tests for AsyncpgCheckpointSaver against a real Postgres."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncEngine

from langgraph_checkpoint_asyncpg import AsyncpgCheckpointSaver, create_checkpointer


def _make_checkpoint(checkpoint_id: str | None = None) -> dict[str, Any]:
    return {
        "v": 1,
        "id": checkpoint_id or str(uuid.uuid4()),
        "ts": "2026-04-21T00:00:00+00:00",
        "channel_values": {"messages": ["hello"], "counter": 42},
        "channel_versions": {"messages": "1", "counter": "1"},
        "versions_seen": {"__start__": {}},
        "updated_channels": ["messages", "counter"],
    }


def _config(thread_id: str, checkpoint_id: str | None = None) -> RunnableConfig:
    cfg: dict[str, Any] = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
    if checkpoint_id:
        cfg["configurable"]["checkpoint_id"] = checkpoint_id
    return cfg  # type: ignore[return-value]


@pytest.mark.asyncio
async def test_put_then_get_roundtrip(clean_engine: AsyncEngine) -> None:
    saver = await create_checkpointer(clean_engine)

    thread_id = "test-thread-1"
    checkpoint = _make_checkpoint()
    metadata = {"source": "input", "step": 0, "writes": None}
    versions = {"messages": "1", "counter": "1"}

    returned = await saver.aput(_config(thread_id), checkpoint, metadata, versions)
    assert returned["configurable"]["checkpoint_id"] == checkpoint["id"]

    got = await saver.aget_tuple(_config(thread_id))
    assert got is not None
    assert got.config["configurable"]["checkpoint_id"] == checkpoint["id"]
    assert got.checkpoint["channel_values"]["messages"] == ["hello"]
    assert got.checkpoint["channel_values"]["counter"] == 42
    assert got.metadata["source"] == "input"


@pytest.mark.asyncio
async def test_get_specific_checkpoint_id(clean_engine: AsyncEngine) -> None:
    saver = await create_checkpointer(clean_engine)
    thread_id = "test-thread-2"

    first = _make_checkpoint()
    second = _make_checkpoint()
    versions = {"messages": "1"}

    await saver.aput(_config(thread_id), first, {"step": 0}, versions)
    await saver.aput(_config(thread_id), second, {"step": 1}, versions)

    got = await saver.aget_tuple(_config(thread_id, first["id"]))
    assert got is not None
    assert got.config["configurable"]["checkpoint_id"] == first["id"]


@pytest.mark.asyncio
async def test_alist_orders_newest_first(clean_engine: AsyncEngine) -> None:
    saver = await create_checkpointer(clean_engine)
    thread_id = "test-thread-3"

    # Insert with deliberately sortable IDs so ORDER BY DESC is deterministic.
    ids = [f"cp-{i:03d}" for i in range(5)]
    for cp_id in ids:
        cp = _make_checkpoint(cp_id)
        await saver.aput(_config(thread_id), cp, {"step": int(cp_id[-3:])}, {})

    seen = [
        t.config["configurable"]["checkpoint_id"] async for t in saver.alist(_config(thread_id))
    ]
    assert seen == list(reversed(ids))


@pytest.mark.asyncio
async def test_alist_respects_limit(clean_engine: AsyncEngine) -> None:
    saver = await create_checkpointer(clean_engine)
    thread_id = "test-thread-4"

    for i in range(5):
        await saver.aput(_config(thread_id), _make_checkpoint(f"cp-{i}"), {"step": i}, {})

    seen = [t async for t in saver.alist(_config(thread_id), limit=2)]
    assert len(seen) == 2


@pytest.mark.asyncio
async def test_put_writes_surfaces_in_pending_writes(clean_engine: AsyncEngine) -> None:
    saver = await create_checkpointer(clean_engine)
    thread_id = "test-thread-5"
    checkpoint = _make_checkpoint()
    await saver.aput(_config(thread_id), checkpoint, {"step": 0}, {})

    write_config = _config(thread_id, checkpoint["id"])
    await saver.aput_writes(
        write_config,
        [("messages", "pending-1"), ("messages", "pending-2")],
        task_id="task-abc",
        task_path="parent/child",
    )

    got = await saver.aget_tuple(write_config)
    assert got is not None
    assert got.pending_writes is not None
    assert len(got.pending_writes) == 2
    task_ids = {tid for tid, _, _ in got.pending_writes}
    assert task_ids == {"task-abc"}


@pytest.mark.asyncio
async def test_adelete_thread_removes_all_rows(clean_engine: AsyncEngine) -> None:
    saver = await create_checkpointer(clean_engine)
    thread_id = "test-thread-6"

    cp = _make_checkpoint()
    await saver.aput(_config(thread_id), cp, {"step": 0}, {"messages": "1"})
    await saver.aput_writes(
        _config(thread_id, cp["id"]),
        [("messages", "pending")],
        task_id="t1",
    )

    assert await saver.aget_tuple(_config(thread_id)) is not None

    await saver.adelete_thread(thread_id)
    assert await saver.aget_tuple(_config(thread_id)) is None


@pytest.mark.asyncio
async def test_sync_methods_raise(clean_engine: AsyncEngine) -> None:
    saver = AsyncpgCheckpointSaver(clean_engine)
    with pytest.raises(NotImplementedError):
        saver.get_tuple(_config("t"))
    with pytest.raises(NotImplementedError):
        saver.put(_config("t"), _make_checkpoint(), {}, {})
    with pytest.raises(NotImplementedError):
        saver.put_writes(_config("t", "x"), [], "t1")
    with pytest.raises(NotImplementedError):
        saver.delete_thread("t")
