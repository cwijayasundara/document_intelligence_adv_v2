# Design — `langgraph-checkpoint-asyncpg`

**Date:** 2026-04-21
**Status:** Spec — awaiting implementation
**Owner:** backend / document-intelligence-adv-v2

## 1. Motivation

LangGraph's only first-party PostgreSQL checkpointer (`langgraph-checkpoint-postgres`) is built on **psycopg3**, which is licensed **LGPL-3.0**. The client's license policy does not permit LGPL dependencies in the product. LangGraph itself and its base checkpointer abstractions (`langgraph-checkpoint`) are MIT.

The existing backend already uses **asyncpg** (Apache-2.0 / PostgreSQL License) through SQLAlchemy 2.0 for all non-checkpointer database access (`backend/src/db/connection.py`). The pipeline currently uses `MemorySaver` (non-durable) as a placeholder; a planned switch to `AsyncPostgresSaver` is blocked by the license issue (see `backend/tests/test_bulk_pipeline.py:484` — the test mocks `AsyncPostgresSaver` from `langgraph.checkpoint.postgres.aio`, confirming the originally intended path).

This spec introduces **`langgraph-checkpoint-asyncpg`** — a new Apache-2.0 package that implements LangGraph's checkpointer contract over asyncpg, with zero LGPL transitive dependencies.

## 2. Scope

### In scope
- A new standalone Python package `langgraph-checkpoint-asyncpg`, sibling to `backend/` and `frontend/` in the monorepo.
- `AsyncpgCheckpointSaver` — subclass of `BaseCheckpointSaver` implementing the minimum async interface needed by this project: `aget_tuple`, `alist`, `aput`, `aput_writes`, `adelete_thread`, `setup`.
- Schema-identical storage to upstream `langgraph-checkpoint-postgres` (same 4 tables, same 9-version migration chain).
- Backend integration: wire the new saver into `src/pipeline/runner.py` and `src/bulk/pipeline.py`, remove the stopgap `database_url_sync` property.

### Out of scope
- Sync methods (`get_tuple`, `list`, `put`, `put_writes`, `delete_thread`) — raise `NotImplementedError`. All application call sites are async.
- Newer upstream methods not used by this project: `adelete_for_runs`, `acopy_thread`, `aprune`.
- Reimplementing `JsonPlusSerializer` — we reuse it from `langgraph-checkpoint` (MIT-licensed, no psycopg dependency).
- A separate `BaseStore` implementation (the LangGraph persistent memory store). This project does not use it today.
- Publishing the package to PyPI. Installed as a local editable dependency via `uv.sources`.

## 3. License posture

| Dependency                     | License               | Status |
|--------------------------------|-----------------------|--------|
| `langgraph` (core)             | MIT                   | OK     |
| `langgraph-checkpoint`         | MIT                   | OK     |
| `langgraph-checkpoint-postgres`| LGPL-3.0 (psycopg3)   | Removed |
| `asyncpg`                      | Apache-2.0            | OK     |
| `sqlalchemy`                   | MIT                   | OK     |
| `langgraph-checkpoint-asyncpg` | Apache-2.0 (new)      | OK     |

The new package's own `LICENSE` file is Apache-2.0 so downstream consumers face no new friction.

## 4. Architecture

```
┌─────────────────────────────────────────────────────────┐
│   LangGraph runtime (ainvoke, aget_state_history, …)    │
└────────────────────────┬────────────────────────────────┘
                         │ async checkpointer interface
┌────────────────────────▼────────────────────────────────┐
│   AsyncpgCheckpointSaver(BaseCheckpointSaver)           │
│   - aget_tuple / alist / aput / aput_writes /           │
│     adelete_thread / setup                              │
│   - serde: JsonPlusSerializer (from langgraph-checkpoint)│
└────────────────────────┬────────────────────────────────┘
                         │ SQLAlchemy Core text() + bindparam
┌────────────────────────▼────────────────────────────────┐
│   AsyncEngine (asyncpg)  — backend/src/db/connection.py │
└─────────────────────────────────────────────────────────┘
```

### Key design decisions

1. **Shared connection pool.** The saver takes an `AsyncEngine` from the application. No second asyncpg pool, no separate DSN, no separate lifecycle wiring. `create_checkpointer` also accepts a DSN string for standalone use outside this backend.
2. **Schema compatibility.** Same tables, columns, indexes, and migration version numbers as upstream. A future migration to or from the official psycopg3 saver needs no data movement.
3. **SQLAlchemy Core, not the ORM.** The saver uses `text()` with named bindparams. This sidesteps the psycopg `%s` vs asyncpg `$1` parameter-style mismatch for free and keeps JSONB/BYTEA casts explicit per-query.
4. **Async-only.** Sync methods raise `NotImplementedError`. The application has no sync call sites.
5. **Reuse `JsonPlusSerializer`.** Upstream's serializer handles LangGraph-internal types (`Send`, `Interrupt`, pydantic models, datetime, etc.) correctly. It lives in `langgraph-checkpoint` (MIT). A custom serializer is a constructor kwarg away if the client later wants full independence from `langgraph-checkpoint`.

## 5. Package layout

```
document_intelligence_adv_v2/
├── backend/
├── frontend/
└── langgraph-checkpoint-asyncpg/
    ├── pyproject.toml
    ├── README.md
    ├── LICENSE                          (Apache-2.0)
    ├── src/
    │   └── langgraph_checkpoint_asyncpg/
    │       ├── __init__.py
    │       ├── saver.py
    │       ├── sql.py
    │       ├── serde.py
    │       ├── migrations.py
    │       └── py.typed
    └── tests/
        ├── conftest.py
        ├── test_saver.py
        ├── test_migrations.py
        └── test_schema_compat.py
```

### `pyproject.toml`

```toml
[project]
name = "langgraph-checkpoint-asyncpg"
version = "0.1.0"
description = "asyncpg-backed LangGraph checkpointer (Apache-2.0)"
license = { text = "Apache-2.0" }
requires-python = ">=3.11"
dependencies = [
    "langgraph-checkpoint>=2.0",
    "asyncpg>=0.30",
    "sqlalchemy[asyncio]>=2.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/langgraph_checkpoint_asyncpg"]
```

### Public API (`__init__.py`)

```python
from langgraph_checkpoint_asyncpg.saver import (
    AsyncpgCheckpointSaver,
    create_checkpointer,
)

__all__ = ["AsyncpgCheckpointSaver", "create_checkpointer"]
```

## 6. `AsyncpgCheckpointSaver`

```python
class AsyncpgCheckpointSaver(BaseCheckpointSaver[str]):
    """LangGraph async checkpointer backed by asyncpg via SQLAlchemy Core.

    Schema-compatible with langgraph-checkpoint-postgres; writes atomic per
    checkpoint via `async with engine.begin()`. No dependency on psycopg.
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

    async def setup(self) -> None: ...
    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None: ...
    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]: ...
    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig: ...
    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None: ...
    async def adelete_thread(self, thread_id: str) -> None: ...

    def get_tuple(self, *a, **kw):
        raise NotImplementedError("Use aget_tuple (async-only saver)")
    # list, put, put_writes, delete_thread: same NotImplementedError pattern
```

### Factory

```python
async def create_checkpointer(
    engine_or_dsn: AsyncEngine | str,
    *,
    auto_setup: bool = True,
) -> AsyncpgCheckpointSaver:
    """Create and (optionally) run setup() on a new saver.

    Accepts either an existing AsyncEngine (the backend's shared engine) or
    a DSN string. When given a DSN, creates and owns a small engine.
    """
```

## 7. Schema and SQL

Tables and migrations are byte-for-byte identical to upstream:

```sql
-- v0: CREATE TABLE IF NOT EXISTS checkpoint_migrations (v INTEGER PRIMARY KEY);

-- v1: CREATE TABLE IF NOT EXISTS checkpoints (
--       thread_id TEXT NOT NULL,
--       checkpoint_ns TEXT NOT NULL DEFAULT '',
--       checkpoint_id TEXT NOT NULL,
--       parent_checkpoint_id TEXT,
--       type TEXT,
--       checkpoint JSONB NOT NULL,
--       metadata JSONB NOT NULL DEFAULT '{}',
--       PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id));

-- v2: CREATE TABLE IF NOT EXISTS checkpoint_blobs (
--       thread_id TEXT NOT NULL, checkpoint_ns TEXT NOT NULL DEFAULT '',
--       channel TEXT NOT NULL, version TEXT NOT NULL, type TEXT NOT NULL,
--       blob BYTEA,
--       PRIMARY KEY (thread_id, checkpoint_ns, channel, version));

-- v3: CREATE TABLE IF NOT EXISTS checkpoint_writes (
--       thread_id TEXT NOT NULL, checkpoint_ns TEXT NOT NULL DEFAULT '',
--       checkpoint_id TEXT NOT NULL, task_id TEXT NOT NULL,
--       idx INTEGER NOT NULL, channel TEXT NOT NULL, type TEXT,
--       blob BYTEA NOT NULL,
--       PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx));

-- v4: ALTER TABLE checkpoint_blobs ALTER COLUMN blob DROP NOT NULL;
-- v5: SELECT 1;  -- no-op slot
-- v6: CREATE INDEX CONCURRENTLY IF NOT EXISTS checkpoints_thread_id_idx        ON checkpoints(thread_id);
-- v7: CREATE INDEX CONCURRENTLY IF NOT EXISTS checkpoint_blobs_thread_id_idx   ON checkpoint_blobs(thread_id);
-- v8: CREATE INDEX CONCURRENTLY IF NOT EXISTS checkpoint_writes_thread_id_idx  ON checkpoint_writes(thread_id);
-- v9: ALTER TABLE checkpoint_writes ADD COLUMN IF NOT EXISTS task_path TEXT NOT NULL DEFAULT '';
```

### Parameter style

Upstream uses psycopg `%s`. Our SQL uses SQLAlchemy `text()` with named bindparams (`:thread_id`), which SQLAlchemy passes to asyncpg's `$1, $2, …` substitution automatically. Example of the `aput` checkpoint upsert:

```python
UPSERT_CHECKPOINTS_SQL = text("""
INSERT INTO checkpoints (thread_id, checkpoint_ns, checkpoint_id,
                         parent_checkpoint_id, checkpoint, metadata)
VALUES (:thread_id, :checkpoint_ns, :checkpoint_id,
        :parent_checkpoint_id,
        :checkpoint, :metadata)
ON CONFLICT (thread_id, checkpoint_ns, checkpoint_id) DO UPDATE SET
    checkpoint = EXCLUDED.checkpoint,
    metadata   = EXCLUDED.metadata
""").bindparams(
    bindparam("checkpoint", type_=JSONB),
    bindparam("metadata",   type_=JSONB),
)
```

### SELECT_SQL

Reused verbatim from upstream (with `:name` bindparams substituted for `%s`). The correlated subqueries for `channel_values` and `pending_writes` are non-trivial; identical semantics are required for correct checkpoint reconstitution.

## 8. Migrations module

```python
async def apply_migrations(conn: AsyncConnection) -> None:
    """Idempotently advance the schema to the latest version.

    - Creates checkpoint_migrations if missing.
    - Reads current max(v). Applies MIGRATIONS[current+1 : len(MIGRATIONS)].
    - Runs CREATE INDEX CONCURRENTLY migrations OUTSIDE any transaction.
    - Each applied migration inserts its version into checkpoint_migrations.
    """
```

Behavior:
- Safe to call on every process startup (`setup()` sets an internal `_setup_done` flag after the first success to avoid repeated DB round-trips).
- Migrations run in two modes:
  - **Transactional** (v0–v5, v9): the `CREATE TABLE`/`ALTER TABLE`/`SELECT 1` statement and the `INSERT INTO checkpoint_migrations` bump commit together inside `async with engine.begin()`.
  - **AUTOCOMMIT** (v6–v8): `CREATE INDEX CONCURRENTLY` cannot run in a transaction, so the runner executes the index DDL via `conn.execution_options(isolation_level="AUTOCOMMIT")`, then issues the version bump as a separate small transaction. A crash between the two leaves the index created but `v` unbumped — rerun is safe because `CREATE INDEX CONCURRENTLY IF NOT EXISTS` is idempotent.
- Failure mid-migration leaves the version table at the last successfully-applied `v`; a rerun resumes from there.

## 9. Serialization

```python
# serde.py
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

__all__ = ["JsonPlusSerializer"]
```

This thin wrapper is a deliberate seam. If the client later wants zero dependency on `langgraph-checkpoint`, replacing this single file (plus a few imports) with a project-owned serializer is the full migration path.

## 10. Backend integration

### `backend/src/bulk/pipeline.py`

Add the `create_checkpointer` helper the tests already expect (`backend/tests/test_bulk_pipeline.py:24`), but import from the new package:

```python
async def create_checkpointer(engine: AsyncEngine) -> AsyncpgCheckpointSaver:
    from langgraph_checkpoint_asyncpg import create_checkpointer as _make
    return await _make(engine, auto_setup=True)
```

### `backend/src/pipeline/runner.py`

- Replace `MemorySaver` with a lazy-initialized `AsyncpgCheckpointSaver` backed by the existing engine.
- Update two call sites that currently use sync state APIs:
  - `runner.py:161` — `list(self._graph.get_state_history(config))` → `[s async for s in self._graph.aget_state_history(config)]`
  - `runner.py:192` — `self._graph.get_state(config)` → `await self._graph.aget_state(config)`

### `backend/src/config/settings.py`

Delete `database_url_sync` (lines 113–118). It was introduced solely to feed psycopg3's sync DSN requirement and is no longer needed.

### `backend/pyproject.toml`

```toml
dependencies = [
    ...,
    "langgraph-checkpoint-asyncpg",
]

[tool.uv.sources]
langgraph-checkpoint-asyncpg = { path = "../langgraph-checkpoint-asyncpg", editable = true }
```

Confirm `langgraph-checkpoint-postgres` is **not** listed (currently absent — keep it that way).

### `backend/tests/test_bulk_pipeline.py::TestCreateCheckpointer`

Update the patched module path from `langgraph.checkpoint.postgres.aio.AsyncPostgresSaver` to `langgraph_checkpoint_asyncpg.AsyncpgCheckpointSaver`. The test intent (verify `setup()` is awaited after construction) remains unchanged.

## 11. Testing strategy

### Package-level (inside `langgraph-checkpoint-asyncpg/tests/`)

| Test file             | What it covers                                                                |
|-----------------------|-------------------------------------------------------------------------------|
| `test_migrations.py`  | Cold-start applies v0–v9; re-run no-op; resume from partial state; CONCURRENTLY indexes succeed outside a transaction |
| `test_saver.py`       | aput→aget_tuple round-trip; alist with filter/before/limit; aput_writes surfaces in pending_writes; adelete_thread removes all three tables' rows for that thread_id |
| `test_schema_compat.py` | After setup, `information_schema` output matches a pinned snapshot of upstream's schema (tables, columns, types, PK, indexes) |
| Interrupt/resume      | Compile a tiny 2-node graph with interrupt_before; invoke; restart a new saver instance on same DB; resume via `Command(resume=...)`; assert final state |

Fixtures: `testcontainers[postgresql]` for a real ephemeral Postgres 15+.

### Backend-level

- Update `backend/tests/test_bulk_pipeline.py::TestCreateCheckpointer` (1 patch path change).
- Update `backend/tests/test_bulk_pipeline.py::test_build_pipeline_with_custom_checkpointer` — no change needed (uses `MemorySaver`).
- New `backend/tests/test_pipeline_runner_persistence.py` — end-to-end: start a pipeline with the real asyncpg saver against a testcontainers Postgres, interrupt at `await_parse_review`, drop and recreate the runner, resume, assert terminal state.

## 12. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| LangGraph evolves `BaseCheckpointSaver` adding new required methods | Pin `langgraph-checkpoint>=2.0,<3.0`. CI against a floor version and a latest version. Add any new methods (or raise `NotImplementedError`) on upgrade. |
| Upstream schema changes (new migration versions) | Test suite's `test_schema_compat.py` pin fails first — forces a deliberate update. |
| asyncpg doesn't auto-cast dict↔JSONB and missing `bindparam(type_=JSONB)` produces silent errors | Integration tests round-trip real checkpoints (not mocks); `test_saver.py` asserts JSONB column values parse back to the source dict. |
| `CREATE INDEX CONCURRENTLY` fails inside a transaction | Migration runner enforces AUTOCOMMIT for index migrations; unit test asserts this path. |
| Pool contention — checkpointer and app sharing a pool could starve each other | Pool size is configurable (`db_pool_size`, already in settings, default 5+5). Monitor; can switch to dedicated pool later if needed — the saver accepts any AsyncEngine. |
| `JsonPlusSerializer` private API shift on langgraph-checkpoint upgrades | Stays fenced in `serde.py`. If it breaks, swap is localized. |

## 13. Acceptance criteria

1. Package `langgraph-checkpoint-asyncpg` builds, installs, and `pytest` passes against a real Postgres container.
2. Schema after `setup()` is byte-identical to upstream's schema on the same DB.
3. Backend `test_bulk_pipeline.py` passes with the new saver patched in.
4. New end-to-end persistence test: a document that hits `interrupt_before=await_parse_review`, with the process restarted, resumes successfully against the same Postgres database and produces the same final state.
5. `pip-audit` / dependency scan shows no LGPL transitive dependency for the backend.
6. The `database_url_sync` property is removed from `backend/src/config/settings.py` and no call sites remain.

## 14. Non-goals / deferred

- Publishing to PyPI (internal-only for now).
- Implementing `adelete_for_runs`, `acopy_thread`, `aprune` — add when an application call site appears.
- Sync-bridge methods — async-only by design.
- A LangGraph `BaseStore` implementation — out of scope; not used by this project.
- Contributing upstream to LangGraph — possible future work once the package is proven.
