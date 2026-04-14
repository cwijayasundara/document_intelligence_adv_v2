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

4. **LangGraph interrupts for human review** — Native `interrupt()` pauses execution and persists state via checkpointer. Clean resume with `Command(resume=...)`.

5. **Agentic RAG with fallback** — `create_react_agent` with tools (search, lookup extractions, get summary) for rich RAG. Falls back to basic retrieve+generate if agent fails.
