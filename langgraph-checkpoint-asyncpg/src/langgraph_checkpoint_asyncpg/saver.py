"""asyncpg-backed implementation of ``BaseCheckpointSaver`` for LangGraph.

Implements the async methods exercised by the LangGraph runtime (``aput``,
``aput_writes``, ``aget_tuple``, ``alist``, ``adelete_thread``, ``setup``).
Sync counterparts raise ``NotImplementedError`` — downstream call sites are
expected to use the async graph API (``ainvoke``, ``aget_state``,
``aget_state_history``).

The wire format and table layout are identical to
``langgraph-checkpoint-postgres``; only the driver and parameter style
differ. Serialization and row <-> tuple conversion live in
``serde_helpers`` to keep this module focused on the saver contract.
"""

from __future__ import annotations

import asyncio
import json
import random
from collections.abc import AsyncIterator, Sequence
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    SerializerProtocol,
    get_checkpoint_id,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from .migrations import apply_migrations
from .serde import JsonPlusSerializer
from .serde_helpers import dump_blobs, dump_writes, row_to_tuple
from .sql import (
    DELETE_THREAD_BLOBS_SQL,
    DELETE_THREAD_CHECKPOINTS_SQL,
    DELETE_THREAD_WRITES_SQL,
    INSERT_CHECKPOINT_WRITES_SQL,
    SELECT_SQL,
    UPSERT_CHECKPOINT_BLOBS_SQL,
    UPSERT_CHECKPOINT_WRITES_SQL,
    UPSERT_CHECKPOINTS_SQL,
)

# NULL_TASK_ID marks pending writes that aren't tied to a specific task yet;
# such writes must be overwritable, so we UPSERT. Everything else is
# insert-once and DO NOTHING on conflict.
NULL_TASK_ID = "00000000-0000-0000-0000-000000000000"


class AsyncpgCheckpointSaver(BaseCheckpointSaver[str]):
    """LangGraph async checkpointer backed by asyncpg via SQLAlchemy Core.

    Parameters
    ----------
    engine:
        An ``AsyncEngine`` configured with the ``postgresql+asyncpg://``
        driver. The saver does not own the engine's lifecycle.
    serde:
        Optional serializer. Defaults to ``JsonPlusSerializer``, which
        handles ``Send``, ``Interrupt``, pydantic models and similar
        LangGraph-internal types correctly.
    """

    def __init__(
        self,
        engine: AsyncEngine,
        serde: SerializerProtocol | None = None,
    ) -> None:
        super().__init__(serde=serde or JsonPlusSerializer())
        self._engine = engine
        self._setup_lock = asyncio.Lock()
        self._setup_done = False

    async def setup(self) -> None:
        """Apply schema migrations idempotently."""
        if self._setup_done:
            return
        async with self._setup_lock:
            if self._setup_done:
                return
            await apply_migrations(self._engine)
            self._setup_done = True

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = get_checkpoint_id(config)

        where = ["thread_id = :thread_id", "checkpoint_ns = :checkpoint_ns"]
        params: dict[str, Any] = {
            "thread_id": thread_id,
            "checkpoint_ns": checkpoint_ns,
        }
        if checkpoint_id is not None:
            where.append("checkpoint_id = :checkpoint_id")
            params["checkpoint_id"] = checkpoint_id

        stmt = text(
            f"{SELECT_SQL.text} WHERE {' AND '.join(where)} ORDER BY checkpoint_id DESC LIMIT 1"
        )

        async with self._engine.connect() as conn:
            result = await conn.execute(stmt, params)
            row = result.mappings().first()

        if row is None:
            return None
        return row_to_tuple(self.serde, row)

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        where, params = self._build_list_predicates(config, filter, before)

        sql = SELECT_SQL.text
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY checkpoint_id DESC"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"

        async with self._engine.connect() as conn:
            result = await conn.stream(text(sql), params)
            async for row in result.mappings():
                yield row_to_tuple(self.serde, row)

    @staticmethod
    def _build_list_predicates(
        config: RunnableConfig | None,
        filter: dict[str, Any] | None,
        before: RunnableConfig | None,
    ) -> tuple[list[str], dict[str, Any]]:
        where: list[str] = []
        params: dict[str, Any] = {}
        if config:
            where.append("thread_id = :thread_id")
            params["thread_id"] = config["configurable"]["thread_id"]
            ns = config["configurable"].get("checkpoint_ns")
            if ns is not None:
                where.append("checkpoint_ns = :checkpoint_ns")
                params["checkpoint_ns"] = ns
            if cp_id := get_checkpoint_id(config):
                where.append("checkpoint_id = :checkpoint_id")
                params["checkpoint_id"] = cp_id
        if filter:
            where.append("metadata @> CAST(:metadata_filter AS JSONB)")
            params["metadata_filter"] = json.dumps(filter)
        if before is not None:
            where.append("checkpoint_id < :before_id")
            params["before_id"] = get_checkpoint_id(before)
        return where, params

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        thread_id: str = config["configurable"]["thread_id"]
        checkpoint_ns: str = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id: str = checkpoint["id"]
        parent_checkpoint_id = config["configurable"].get("checkpoint_id")

        blob_rows = dump_blobs(
            self.serde,
            thread_id,
            checkpoint_ns,
            checkpoint.get("channel_values", {}),
            new_versions,
        )
        # Stored checkpoint JSONB strips channel_values; live values live in
        # checkpoint_blobs, rebuilt on aget_tuple via SELECT_SQL.
        checkpoint_row: dict[str, Any] = {**checkpoint, "channel_values": {}}

        async with self._engine.begin() as conn:
            if blob_rows:
                await conn.execute(UPSERT_CHECKPOINT_BLOBS_SQL, blob_rows)
            await conn.execute(
                UPSERT_CHECKPOINTS_SQL,
                {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": checkpoint_id,
                    "parent_checkpoint_id": parent_checkpoint_id,
                    "checkpoint": checkpoint_row,
                    "metadata": dict(metadata),
                },
            )

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        rows = dump_writes(
            self.serde,
            config["configurable"]["thread_id"],
            config["configurable"].get("checkpoint_ns", ""),
            config["configurable"]["checkpoint_id"],
            task_id,
            task_path,
            writes,
        )
        if not rows:
            return

        stmt = (
            UPSERT_CHECKPOINT_WRITES_SQL
            if task_id == NULL_TASK_ID
            else INSERT_CHECKPOINT_WRITES_SQL
        )
        async with self._engine.begin() as conn:
            await conn.execute(stmt, rows)

    async def adelete_thread(self, thread_id: str) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(DELETE_THREAD_WRITES_SQL, {"thread_id": thread_id})
            await conn.execute(DELETE_THREAD_BLOBS_SQL, {"thread_id": thread_id})
            await conn.execute(DELETE_THREAD_CHECKPOINTS_SQL, {"thread_id": thread_id})

    def get_next_version(self, current: str | None, channel: None = None) -> str:
        if current is None:
            current_v = 0
        elif isinstance(current, int):
            current_v = current
        else:
            current_v = int(current.split(".")[0])
        return f"{current_v + 1:032}.{random.random():016}"

    _SYNC_ERROR = "AsyncpgCheckpointSaver is async-only; use the a-prefixed methods"

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        raise NotImplementedError(self._SYNC_ERROR)

    def list(self, *args: Any, **kwargs: Any) -> Any:  # noqa: A003
        raise NotImplementedError(self._SYNC_ERROR)

    def put(self, *args: Any, **kwargs: Any) -> RunnableConfig:
        raise NotImplementedError(self._SYNC_ERROR)

    def put_writes(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError(self._SYNC_ERROR)

    def delete_thread(self, thread_id: str) -> None:
        raise NotImplementedError(self._SYNC_ERROR)
