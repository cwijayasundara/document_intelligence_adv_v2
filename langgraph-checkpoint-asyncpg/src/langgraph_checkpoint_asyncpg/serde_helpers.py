"""Serialization helpers shared by the saver.

These are module-level because they are pure functions of the serializer
and the row data; keeping them out of the main class file keeps the class
focused on the async ``BaseCheckpointSaver`` contract.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    WRITES_IDX_MAP,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    SerializerProtocol,
)


def dump_blobs(
    serde: SerializerProtocol,
    thread_id: str,
    checkpoint_ns: str,
    values: dict[str, Any],
    versions: ChannelVersions,
) -> list[dict[str, Any]]:
    if not versions:
        return []
    rows: list[dict[str, Any]] = []
    for channel, version in versions.items():
        if channel in values:
            type_, blob = serde.dumps_typed(values[channel])
        else:
            type_, blob = "empty", None
        rows.append(
            {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "channel": channel,
                "version": str(version),
                "type": type_,
                "blob": blob,
            }
        )
    return rows


def load_blobs(
    serde: SerializerProtocol,
    blob_values: list[tuple[bytes, bytes, bytes]] | None,
) -> dict[str, Any]:
    if not blob_values:
        return {}
    return {
        channel.decode(): serde.loads_typed((type_.decode(), blob))
        for channel, type_, blob in blob_values
        if type_.decode() != "empty"
    }


def dump_writes(
    serde: SerializerProtocol,
    thread_id: str,
    checkpoint_ns: str,
    checkpoint_id: str,
    task_id: str,
    task_path: str,
    writes: Sequence[tuple[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, (channel, value) in enumerate(writes):
        type_, blob = serde.dumps_typed(value)
        rows.append(
            {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
                "task_id": task_id,
                "task_path": task_path,
                "idx": WRITES_IDX_MAP.get(channel, idx),
                "channel": channel,
                "type": type_,
                "blob": blob,
            }
        )
    return rows


def load_writes(
    serde: SerializerProtocol,
    writes: list[tuple[bytes, bytes, bytes, bytes]] | None,
) -> list[tuple[str, str, Any]]:
    if not writes:
        return []
    return [
        (
            task_id.decode(),
            channel.decode(),
            serde.loads_typed((type_.decode(), blob)),
        )
        for task_id, channel, type_, blob in writes
    ]


def row_to_tuple(serde: SerializerProtocol, row: Any) -> CheckpointTuple:
    stored_checkpoint: dict[str, Any] = dict(row["checkpoint"])
    channel_values = load_blobs(serde, row["channel_values"])
    checkpoint: Checkpoint = {
        **stored_checkpoint,
        "channel_values": channel_values,
    }  # type: ignore[assignment]

    metadata: CheckpointMetadata = dict(row["metadata"])  # type: ignore[assignment]

    config: RunnableConfig = {
        "configurable": {
            "thread_id": row["thread_id"],
            "checkpoint_ns": row["checkpoint_ns"],
            "checkpoint_id": row["checkpoint_id"],
        }
    }
    parent_config: RunnableConfig | None = None
    if row["parent_checkpoint_id"] is not None:
        parent_config = {
            "configurable": {
                "thread_id": row["thread_id"],
                "checkpoint_ns": row["checkpoint_ns"],
                "checkpoint_id": row["parent_checkpoint_id"],
            }
        }

    pending_writes = load_writes(serde, row["pending_writes"])

    return CheckpointTuple(
        config=config,
        checkpoint=checkpoint,
        metadata=metadata,
        parent_config=parent_config,
        pending_writes=pending_writes,
    )
