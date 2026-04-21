"""SQL constants for the asyncpg-backed LangGraph checkpointer.

Schema and statements are kept byte-identical (modulo parameter style) to
``langgraph-checkpoint-postgres`` so a database written by either
implementation can be read by the other.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import BYTEA, JSONB


@dataclass(frozen=True)
class Migration:
    version: int
    statement: str
    concurrent: bool = False


MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        0,
        """
        CREATE TABLE IF NOT EXISTS checkpoint_migrations (
            v INTEGER PRIMARY KEY
        )
        """,
    ),
    Migration(
        1,
        """
        CREATE TABLE IF NOT EXISTS checkpoints (
            thread_id TEXT NOT NULL,
            checkpoint_ns TEXT NOT NULL DEFAULT '',
            checkpoint_id TEXT NOT NULL,
            parent_checkpoint_id TEXT,
            type TEXT,
            checkpoint JSONB NOT NULL,
            metadata JSONB NOT NULL DEFAULT '{}',
            PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
        )
        """,
    ),
    Migration(
        2,
        """
        CREATE TABLE IF NOT EXISTS checkpoint_blobs (
            thread_id TEXT NOT NULL,
            checkpoint_ns TEXT NOT NULL DEFAULT '',
            channel TEXT NOT NULL,
            version TEXT NOT NULL,
            type TEXT NOT NULL,
            blob BYTEA,
            PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
        )
        """,
    ),
    Migration(
        3,
        """
        CREATE TABLE IF NOT EXISTS checkpoint_writes (
            thread_id TEXT NOT NULL,
            checkpoint_ns TEXT NOT NULL DEFAULT '',
            checkpoint_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            idx INTEGER NOT NULL,
            channel TEXT NOT NULL,
            type TEXT,
            blob BYTEA NOT NULL,
            PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
        )
        """,
    ),
    Migration(
        4,
        "ALTER TABLE checkpoint_blobs ALTER COLUMN blob DROP NOT NULL",
    ),
    Migration(
        5,
        "SELECT 1",
    ),
    Migration(
        6,
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
        "checkpoints_thread_id_idx ON checkpoints(thread_id)",
        concurrent=True,
    ),
    Migration(
        7,
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
        "checkpoint_blobs_thread_id_idx ON checkpoint_blobs(thread_id)",
        concurrent=True,
    ),
    Migration(
        8,
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
        "checkpoint_writes_thread_id_idx ON checkpoint_writes(thread_id)",
        concurrent=True,
    ),
    Migration(
        9,
        "ALTER TABLE checkpoint_writes ADD COLUMN IF NOT EXISTS task_path TEXT NOT NULL DEFAULT ''",
    ),
)

LATEST_VERSION: int = MIGRATIONS[-1].version


SELECT_SQL = text("""
SELECT
    thread_id,
    checkpoint,
    checkpoint_ns,
    checkpoint_id,
    parent_checkpoint_id,
    metadata,
    (
        SELECT array_agg(array[bl.channel::bytea, bl.type::bytea, bl.blob])
        FROM jsonb_each_text(checkpoint -> 'channel_versions')
        INNER JOIN checkpoint_blobs bl
            ON bl.thread_id = checkpoints.thread_id
            AND bl.checkpoint_ns = checkpoints.checkpoint_ns
            AND bl.channel = jsonb_each_text.key
            AND bl.version = jsonb_each_text.value
    ) AS channel_values,
    (
        SELECT array_agg(
            array[cw.task_id::text::bytea, cw.channel::bytea, cw.type::bytea, cw.blob]
            ORDER BY cw.task_id, cw.idx
        )
        FROM checkpoint_writes cw
        WHERE cw.thread_id = checkpoints.thread_id
            AND cw.checkpoint_ns = checkpoints.checkpoint_ns
            AND cw.checkpoint_id = checkpoints.checkpoint_id
    ) AS pending_writes
FROM checkpoints
""")


UPSERT_CHECKPOINT_BLOBS_SQL = text("""
INSERT INTO checkpoint_blobs
    (thread_id, checkpoint_ns, channel, version, type, blob)
VALUES
    (:thread_id, :checkpoint_ns, :channel, :version, :type, :blob)
ON CONFLICT (thread_id, checkpoint_ns, channel, version) DO NOTHING
""").bindparams(bindparam("blob", type_=BYTEA))


UPSERT_CHECKPOINTS_SQL = text("""
INSERT INTO checkpoints
    (thread_id, checkpoint_ns, checkpoint_id,
     parent_checkpoint_id, checkpoint, metadata)
VALUES
    (:thread_id, :checkpoint_ns, :checkpoint_id,
     :parent_checkpoint_id, :checkpoint, :metadata)
ON CONFLICT (thread_id, checkpoint_ns, checkpoint_id) DO UPDATE SET
    checkpoint = EXCLUDED.checkpoint,
    metadata   = EXCLUDED.metadata
""").bindparams(
    bindparam("checkpoint", type_=JSONB),
    bindparam("metadata", type_=JSONB),
)


UPSERT_CHECKPOINT_WRITES_SQL = text("""
INSERT INTO checkpoint_writes
    (thread_id, checkpoint_ns, checkpoint_id,
     task_id, task_path, idx, channel, type, blob)
VALUES
    (:thread_id, :checkpoint_ns, :checkpoint_id,
     :task_id, :task_path, :idx, :channel, :type, :blob)
ON CONFLICT (thread_id, checkpoint_ns, checkpoint_id, task_id, idx) DO UPDATE SET
    channel = EXCLUDED.channel,
    type    = EXCLUDED.type,
    blob    = EXCLUDED.blob
""").bindparams(bindparam("blob", type_=BYTEA))


INSERT_CHECKPOINT_WRITES_SQL = text("""
INSERT INTO checkpoint_writes
    (thread_id, checkpoint_ns, checkpoint_id,
     task_id, task_path, idx, channel, type, blob)
VALUES
    (:thread_id, :checkpoint_ns, :checkpoint_id,
     :task_id, :task_path, :idx, :channel, :type, :blob)
ON CONFLICT (thread_id, checkpoint_ns, checkpoint_id, task_id, idx) DO NOTHING
""").bindparams(bindparam("blob", type_=BYTEA))


DELETE_THREAD_CHECKPOINTS_SQL = text("DELETE FROM checkpoints WHERE thread_id = :thread_id")
DELETE_THREAD_BLOBS_SQL = text("DELETE FROM checkpoint_blobs WHERE thread_id = :thread_id")
DELETE_THREAD_WRITES_SQL = text("DELETE FROM checkpoint_writes WHERE thread_id = :thread_id")


SELECT_MAX_MIGRATION_VERSION_SQL = text("SELECT COALESCE(MAX(v), -1) FROM checkpoint_migrations")

INSERT_MIGRATION_VERSION_SQL = text(
    "INSERT INTO checkpoint_migrations (v) VALUES (:v) ON CONFLICT DO NOTHING"
)
