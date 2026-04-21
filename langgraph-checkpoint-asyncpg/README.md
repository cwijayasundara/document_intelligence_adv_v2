# langgraph-checkpoint-asyncpg

An **Apache-2.0** PostgreSQL checkpointer for [LangGraph](https://github.com/langchain-ai/langgraph), built on [asyncpg](https://github.com/MagicStack/asyncpg) via [SQLAlchemy](https://www.sqlalchemy.org/) — with **no psycopg dependency**.

The official `langgraph-checkpoint-postgres` package uses psycopg3, which is LGPL-3.0. This package provides a drop-in async alternative for projects that require an Apache-2.0-compatible dependency tree.

## Features

- Implements `langgraph.checkpoint.base.BaseCheckpointSaver` (async methods).
- **Schema-compatible** with the official `langgraph-checkpoint-postgres` — the same four tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`) and the same nine-version migration chain.
- Accepts an existing SQLAlchemy `AsyncEngine` (share your app's pool) or creates one from a DSN.
- Reuses LangGraph's `JsonPlusSerializer` for correct handling of `Send`, `Interrupt`, pydantic models, etc. (MIT — no LGPL).

## Install

```bash
pip install langgraph-checkpoint-asyncpg
```

## Usage

```python
import os
from sqlalchemy.ext.asyncio import create_async_engine
from langgraph_checkpoint_asyncpg import create_checkpointer

# Read DSN from the environment; never hard-code credentials.
engine = create_async_engine(os.environ["DATABASE_URL"])

saver = await create_checkpointer(engine)

# Then pass to a compiled graph:
app = graph.compile(checkpointer=saver)
```

### With a DSN string

```python
import os
saver = await create_checkpointer(os.environ["DATABASE_URL"])
```

The DSN must use the `postgresql+asyncpg://` scheme.

## Scope

This package implements the async interface only (`aget_tuple`, `alist`, `aput`, `aput_writes`, `adelete_thread`, `setup`). Sync methods raise `NotImplementedError`.

## Testing

The test suite runs against a real PostgreSQL instance booted by `testcontainers`. A running Docker daemon is required.

```bash
uv sync --all-extras
uv run pytest
```

On macOS + Python 3.13, uv marks editable-install `.pth` files as "hidden", which Python then skips. If `import langgraph_checkpoint_asyncpg` fails right after `uv sync`, run:

```bash
chflags nohidden .venv/lib/python*/site-packages/*.pth
```

Linux and CI are unaffected.

Test suites:
- `tests/test_migrations.py` — cold-start, idempotent rerun, resume-from-partial.
- `tests/test_saver.py` — round-trip, filtering, pending_writes, thread delete.
- `tests/test_schema_compat.py` — column/type/index snapshot against upstream's schema.

## License

Apache-2.0. See `LICENSE`.
