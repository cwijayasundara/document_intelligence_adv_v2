# PE Document Intelligence — Backend

FastAPI backend for the PE Document Intelligence platform. Processes Private Equity documents (LPAs, Subscription Agreements, Side Letters) through a unified LangGraph pipeline with confidence-based human-in-the-loop gates.

## Architecture

### Unified Pipeline

One LangGraph pipeline serves both single-document and bulk flows. Confidence gates apply universally — documents with low parse confidence pause for human review regardless of whether they came from a single upload or a bulk job.

```
parse ──→ [route_after_parse] ──→ summarize ──→ classify ──→ extract ──→ [route_after_extract] ──→ ingest ──→ finalize
              │                                                                   │
              └─→ await_parse_review ──→ summarize                               └─→ await_extraction_review ──→ ingest
```

Routing gates:
- **`route_after_parse`** — if `parse_confidence_pct >= 90%`, continue; else pause for user to edit
- **`route_after_extract`** — if no fields need review, continue; else pause for user approval

Paused documents use LangGraph's `interrupt()` to save state. When the user edits content or approves extractions, the pipeline auto-resumes.

### Agent Layer

Plain async functions (no DeepAgents SDK) using LangChain's `init_chat_model()` for provider-agnostic LLM access:

| Function | Purpose |
|----------|---------|
| `classify_document()` | Classify PE documents into categories |
| `extract_fields()` | Extract structured fields with dynamic Pydantic models |
| `judge_extraction()` | Evaluate extraction confidence per field |
| `summarize_document()` | Generate PE-aware summaries |
| `retrieve_chunks()` + `generate_answer()` | Basic RAG |
| `agentic_rag_query()` | Agentic RAG with query reformulation and multi-tool access |

All agents use composable decorators: `@with_retry`, `@with_telemetry`, plus built-in PII filtering and context-window truncation.

### Agent Memory

Two-tier memory integrated with the pipeline:
- **Short-term**: `pipeline_context` carried through `DocumentState` across nodes
- **Long-term**: LangGraph's `InMemoryStore` (upgradeable to `AsyncPostgresStore`) for classification corrections, extraction patterns, and user preferences

## Tech Stack

- **FastAPI** — async HTTP API
- **LangGraph** — stateful pipeline orchestration with checkpointing and interrupts
- **LangChain** — LLM abstraction via `init_chat_model()`
- **OpenAI / Anthropic / Gemini** — any provider supported by `init_chat_model()`
- **Reducto** — document parsing with confidence scores
- **Weaviate** — vector store for RAG with hybrid search + cross-encoder reranking
- **PostgreSQL** — document metadata, extraction results, bulk job tracking
- **SQLAlchemy 2.0** + **asyncpg** — async ORM
- **Alembic** — database migrations
- **pytest** + **pytest-asyncio** — testing

## Getting Started

```bash
# Install dependencies (creates .venv and installs all packages)
uv sync

# Set up environment
cp .env.example .env
# Edit .env with OPENAI_API_KEY, REDUCTO_API_KEY, DATABASE_URL, WEAVIATE_URL

# Run migrations
uv run alembic upgrade head

# Start server (MUST use uv run or .venv/bin/uvicorn — see below)
uv run uvicorn src.main:app --reload
```

Server runs on `http://localhost:8000`. Docs at `/docs`.

### ⚠️ Important: Always use the project's virtualenv

Running `uvicorn` or `alembic` directly from your shell will use whatever Python is first on your PATH — likely your system Python, which **does not have the project's dependencies** (weaviate, langchain, etc.). This causes `ModuleNotFoundError: No module named 'weaviate'` (or similar).

Use one of these to ensure the project's `.venv` is used:

```bash
# Option 1 (recommended): uv run
uv run uvicorn src.main:app --reload
uv run alembic upgrade head
uv run pytest

# Option 2: explicit path to venv binaries
.venv/bin/uvicorn src.main:app --reload
.venv/bin/alembic upgrade head
.venv/bin/pytest

# Option 3: activate the venv in your shell
source .venv/bin/activate
uvicorn src.main:app --reload
```

### Database Migrations

Alembic revisions can be viewed/managed with:

```bash
uv run alembic current           # Show current revision
uv run alembic heads             # Show head revisions (should be 1)
uv run alembic history           # Show full migration history
uv run alembic upgrade head      # Apply pending migrations
uv run alembic downgrade -1      # Roll back one migration
uv run alembic stamp <revision>  # Manually set revision without running migrations
```

If you see `Multiple head revisions are present`, check `alembic/versions/` for duplicate revision IDs — every migration must have a unique `revision = "..."` value.

## Project Structure

```
src/
  agents/                        # Agent layer
    classifier.py                # classify_document() function
    extractor.py                 # extract_fields() function
    judge.py                     # judge_extraction() function
    summarizer.py                # summarize_document() function
    rag_retriever.py             # retrieve_chunks() + generate_answer()
    llm.py                       # get_llm() factory using init_chat_model()
    schemas/                     # Pydantic response models
    middleware/
      pii_filter.py              # PII redaction patterns
      decorators/                # Composable middleware decorators
        pii.py                   # @with_pii_filter
        retry.py                 # @with_retry
        rate_limit.py            # @with_rate_limit
        fallback.py              # @with_fallback
        context_window.py        # @with_context_window
        telemetry.py             # @with_telemetry
    memory/
      store.py                   # LangGraph Store integration
      short_term.py              # In-memory conversation history
      long_term.py               # (legacy) PostgreSQL key-value store

  api/
    app.py                       # FastAPI factory + lifespan
    routes.py                    # Router registration
    seed_data.py                 # Default categories + LPA extraction fields
    dependencies.py              # FastAPI dependency providers
    middleware/                  # Request-level middleware
    routers/
      pipeline.py                # /pipeline/{id}/{start,resume,retry,status}
      documents.py               # Document CRUD + upload
      parse.py                   # Parse endpoints (+ auto-resume on edit)
      classify.py                # Classification endpoint
      extract.py                 # Extraction endpoints (+ auto-resume on review)
      summarize.py               # Summarization endpoint
      ingest.py                  # Weaviate ingestion
      rag.py                     # RAG query (uses agentic RAG)
      bulk.py                    # Bulk upload + job management
      stream.py                  # SSE for job/document progress
      audit.py                   # Audit log
      events.py                  # Event streaming
      data_agent.py              # Analytics agent
    schemas/                     # Request/response Pydantic models

  bulk/                          # LangGraph pipeline
    pipeline.py                  # StateGraph with conditional edges
    state.py                     # DocumentState TypedDict
    nodes.py                     # Pipeline node implementations
    gates.py                     # Routing functions (route_after_parse, route_after_extract)
    wait_nodes.py                # interrupt() nodes for human review
    service.py                   # BulkJobService
    event_bus.py                 # SSE event streaming

  pipeline/
    runner.py                    # PipelineRunner (start/resume/retry)

  rag/                           # RAG infrastructure
    agent.py                     # Agentic RAG with tools (search_documents, lookup_extractions, get_document_summary)
    weaviate_client.py           # Weaviate wrapper
    chunker.py                   # Document chunker
    reranker.py                  # Cross-encoder reranker
    formatting.py                # Shared citation/context formatting

  services/                      # Business logic
    state_machine.py             # Document status transitions
    parse_service.py             # Reducto integration
    summarize_service.py         # Summary with disk cache
    extraction_service.py        # Extractor + judge pipeline with cache
    rag_service.py               # RAG query orchestration
    ingest_service.py            # Weaviate ingestion
    hashing.py                   # Shared content hashing

  data_agent/                    # NL → SQL analytics agent
    agent.py
    executor.py
    schema.py

  db/                            # Database layer
    models/                      # SQLAlchemy ORM models
    repositories/                # Data access layer
    enums.py                     # DocumentStatus, BulkJobStatus
    connection.py

  config/
    settings.py                  # Pydantic settings

  storage/                       # File storage
  parser/                        # Reducto client
  audit/                         # Audit event queue

alembic/versions/                # Database migrations
tests/                           # pytest test suite
```

## API Endpoints

### Pipeline
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/pipeline/{doc_id}/start` | Start unified pipeline |
| POST | `/api/v1/pipeline/{doc_id}/resume` | Resume from human review gate |
| POST | `/api/v1/pipeline/{doc_id}/retry/{node}` | Retry a failed node |
| GET | `/api/v1/pipeline/{doc_id}/status` | Get per-node status |

### Documents
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/documents/upload` | Upload a document (auto-starts pipeline) |
| GET | `/api/v1/documents` | List documents |
| GET | `/api/v1/documents/{id}` | Get document details |

### Per-Step Endpoints (still available for manual control)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/parse/{id}` | Trigger parse |
| PUT | `/api/v1/parse/{id}/content` | Save edited content (auto-resumes pipeline if paused) |
| POST | `/api/v1/classify/{id}` | Classify document |
| POST | `/api/v1/extract/{id}` | Extract fields |
| PUT | `/api/v1/extract/{id}/results` | Update extracted values (auto-resumes pipeline) |
| POST | `/api/v1/summarize/{id}` | Generate summary |
| POST | `/api/v1/ingest/{id}` | Ingest to Weaviate |

### RAG & Analytics
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/rag/search` | Agentic RAG query |
| POST | `/api/v1/data-agent/query` | Natural language → SQL analytics |

### Bulk
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/bulk/upload` | Upload multiple docs, create job |
| GET | `/api/v1/bulk/jobs` | List jobs |
| GET | `/api/v1/bulk/jobs/{id}` | Job detail with per-document status |

### Streaming
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/stream/jobs/{id}` | SSE for bulk job progress |
| GET | `/api/v1/stream/documents/{id}` | SSE for single document progress |

## Document Status Lifecycle

```
uploaded → processing ──→ parsed ──→ classified ──→ extracted ──→ summarized ──→ ingested
                      │          │                │
                      │          └─→ awaiting_parse_review ──→ edited ──→ ...
                      │
                      └─→ awaiting_extraction_review ──→ extracted ──→ ...
```

## Middleware Decorators

All agent functions get composable middleware:

```python
@with_retry(max_retries=3)                    # Exponential backoff on 429/5xx
@with_telemetry(node_name="classify")         # Duration + success/failure logging
async def classify_document(...) -> ClassificationResult:
    ...
```

Available decorators:
- **`@with_pii_filter`** — Redact SSN, email, phone, bank accounts (preserves PE financial terms)
- **`@with_retry`** — Exponential backoff with jitter on retryable HTTP codes
- **`@with_rate_limit`** — Per-pipeline-run call tracking via `contextvars`
- **`@with_fallback`** — Alternate model on exhausted retries
- **`@with_context_window`** — Truncate oversized content
- **`@with_telemetry`** — Timing + structured logging

## Configuration

All settings via environment variables (`.env`) or `config.yml`:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_MODEL` | Default model (e.g. `gpt-5.4-mini`) |
| `OPENAI_FALLBACK_MODEL` | Fallback on exhausted retries |
| `REDUCTO_API_KEY` | Reducto API key |
| `REDUCTO_BASE_URL` | Reducto API base URL |
| `DATABASE_URL` | PostgreSQL async URL |
| `WEAVIATE_URL` | Weaviate server URL |
| `PARSE_CONFIDENCE_THRESHOLD` | Threshold for parse review gate (default 90) |
| `DATA_AGENT_MODEL` | Model for NL→SQL agent (default `gpt-5.3-codex`) |
| `LLM_MAX_RETRIES` | Default max retries (default 3) |
| `AGENT_MAX_LLM_CALLS` | Per-run LLM call limit (default 50) |

## Testing

```bash
uv run pytest                              # Run all tests
uv run pytest tests/test_gates.py          # Run specific test file
uv run pytest --cov=src                    # With coverage
```

Current test coverage:
- **Pipeline routing** (`test_gates.py`) — 15 tests
- **Middleware decorators** (`test_decorators.py`) — 15 tests
- **PipelineRunner** (`test_pipeline_runner.py`) — 10 tests
- **State machine** (`test_state_machine.py`) — 23 tests
- **Agent functions** (classifier, extractor, judge, summarizer) — 30+ tests
- **PII filter** — full pattern coverage

## Pipeline Checkpointer

The LangGraph pipeline persists its state through **`langgraph-checkpoint-asyncpg`** — a first-party Apache-2.0 package (sibling to `backend/`) that implements LangGraph's checkpointer on top of asyncpg. It replaces the upstream `langgraph-checkpoint-postgres`, which depends on psycopg3 (LGPL-3.0).

Key properties:
- **Schema-identical** to upstream (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`) — you can switch to/from the official saver without data migration.
- **Shared connection pool** — the saver uses the same `AsyncEngine` as the rest of the backend (`src/db/connection.py`), so no new pool configuration is required.
- **Lazy setup** — migrations run idempotently on first use; no manual step required at startup.
- **Durable interrupts** — a document paused at `interrupt_before=await_parse_review` survives a process restart and resumes cleanly via `Command(resume=...)`.

No env vars to configure. The saver reads from the existing `DATABASE_URL`.

### Testing the pipeline with the new checkpointer

#### 1. Start the infrastructure

```bash
# From the repo root
docker compose up -d postgres
```

#### 2. Install deps and fix a macOS-only .pth flag

```bash
cd backend
uv sync
# macOS + Python 3.13 only — uv marks editable-install .pth files as
# hidden, and Python 3.13 skips hidden .pth files. Clear the flag:
chflags nohidden .venv/lib/python3.13/site-packages/*.pth
```

Rerun `chflags nohidden` after any `uv sync`/`uv add` that rewrites the `.pth` file. Linux and CI are unaffected.

#### 3. Apply backend migrations (unrelated to the checkpointer tables)

```bash
uv run alembic upgrade head
```

#### 4. Quick smoke test — the saver imports and talks to Postgres

Save as `/tmp/smoke_checkpointer.py` (or run inline):

```python
import asyncio, os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from langgraph_checkpoint_asyncpg import create_checkpointer
from langgraph_checkpoint_asyncpg.sql import LATEST_VERSION


async def main() -> None:
    engine = create_async_engine(os.environ["DATABASE_URL"])
    saver = await create_checkpointer(engine)  # runs migrations idempotently

    async with engine.connect() as conn:
        v = (await conn.execute(text("SELECT MAX(v) FROM checkpoint_migrations"))).scalar_one()
    assert v == LATEST_VERSION, f"schema at v{v}, expected v{LATEST_VERSION}"
    print(f"checkpointer ready: schema v{v}, 4 tables created")
    await engine.dispose()


asyncio.run(main())
```

```bash
DATABASE_URL="$(grep ^DATABASE_URL .env | cut -d= -f2-)" uv run python /tmp/smoke_checkpointer.py
```

Expected output:

```
checkpointer ready: schema v9, 4 tables created
```

#### 5. End-to-end interrupt / resume test

Proves state durability across process restarts — the main thing the new saver gives you over `MemorySaver`.

```python
# /tmp/e2e_interrupt.py
import asyncio, os
from typing import TypedDict
from sqlalchemy.ext.asyncio import create_async_engine
from langgraph.graph import END, StateGraph
from langgraph.types import Command, interrupt
from langgraph_checkpoint_asyncpg import create_checkpointer


class S(TypedDict, total=False):
    step: int
    note: str


def start(s: S) -> S:     return {"step": (s.get("step") or 0) + 1, "note": "started"}
def review(s: S) -> S:    return {"step": s["step"] + 1, "note": f"resumed:{interrupt({'approve?': True})}"}
def finish(s: S) -> S:    return {"step": s["step"] + 1, "note": s["note"] + "+done"}


async def main() -> None:
    engine = create_async_engine(os.environ["DATABASE_URL"])

    g = StateGraph(S)
    for name, fn in [("start", start), ("review", review), ("finish", finish)]:
        g.add_node(name, fn)
    g.set_entry_point("start")
    g.add_edge("start", "review")
    g.add_edge("review", "finish")
    g.add_edge("finish", END)

    cfg = {"configurable": {"thread_id": "smoke-e2e"}}

    # Process "A": run up to the interrupt.
    saver_a = await create_checkpointer(engine)
    app_a = g.compile(checkpointer=saver_a)
    await app_a.ainvoke({"step": 0}, cfg)

    # Process "B" — simulated fresh process, new saver instance, same DB.
    saver_b = await create_checkpointer(engine)
    app_b = g.compile(checkpointer=saver_b)
    result = await app_b.ainvoke(Command(resume="approved"), cfg)
    assert result["step"] == 3 and "resumed:approved+done" in result["note"]
    print("interrupt/resume across saver instances: OK")
    await engine.dispose()


asyncio.run(main())
```

```bash
DATABASE_URL="$(grep ^DATABASE_URL .env | cut -d= -f2-)" uv run python /tmp/e2e_interrupt.py
```

#### 6. Start the backend and exercise a real pipeline

```bash
uv run uvicorn src.main:app --reload
```

Then, in another shell:

```bash
# Upload a document (starts the pipeline automatically)
curl -F 'file=@docs/LPA_Horizon_Equity_Partners_IV.pdf' \
     http://localhost:8000/api/v1/documents/upload

# Get the document id from the response, then:
curl http://localhost:8000/api/v1/pipeline/<doc-id>/status
```

Restart the uvicorn process mid-pipeline. Hit `/status` again — the returned `next_nodes` and `node_statuses` should survive the restart (this was lost with `MemorySaver`).

#### 7. Run the checkpointer package's own tests (optional)

The package ships its own test suite against a real Postgres via `testcontainers`. Requires a running Docker daemon.

```bash
cd ../langgraph-checkpoint-asyncpg
uv sync --all-extras
chflags nohidden .venv/lib/python*/site-packages/*.pth 2>/dev/null   # macOS only
uv run pytest
```

Tests cover migrations (cold-start, rerun, resume-from-partial), saver behavior (round-trip, filter/before/limit, pending_writes, thread delete), and schema compatibility with the upstream table layout.

#### 8. Verify the LGPL dependency is gone

```bash
uv pip list | grep -i psycopg
# (no output expected)
uv pip list | grep -i langgraph-checkpoint
# langgraph-checkpoint           2.x.y       (MIT)
# langgraph-checkpoint-asyncpg   0.1.0       (Apache-2.0, local editable)
```

## Creating New Migrations

```bash
uv run alembic revision -m "description"   # Create new migration
uv run alembic upgrade head                # Apply pending migrations
uv run alembic downgrade -1                # Rollback last migration
```

**Note:** Every migration file in `alembic/versions/` must have a unique `revision = "..."` ID. Duplicate revision IDs will cause "Multiple head revisions" errors and block upgrades.

## Key Design Decisions

1. **One pipeline for single + bulk** — Confidence gates are data-driven, not mode-driven. A bulk upload of 10 docs may pause 3 for review while the other 7 auto-complete.

2. **Plain functions over SDK agents** — Direct OpenAI/LangChain calls via `init_chat_model()` keep the code simple and provider-agnostic. DeepAgents SDK was removed.

3. **Decorators over framework middleware** — LangGraph has no built-in middleware system. Python decorators give composable cross-cutting concerns that wrap agent functions directly.

4. **LangGraph interrupts for human review** — Native `interrupt()` pauses execution and persists state via a custom asyncpg-backed checkpointer (`langgraph-checkpoint-asyncpg`, sibling package). Clean resume with `Command(resume=...)`; state survives process restarts.

5. **Agentic RAG with fallback** — `create_react_agent` with tools (search, lookup extractions, get summary) for rich RAG. Falls back to basic retrieve+generate if agent fails.
