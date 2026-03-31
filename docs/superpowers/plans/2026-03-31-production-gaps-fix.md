# Production Gaps Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close 10 production gaps identified from the LangChain productionizing guide — multi-tenancy, persistent checkpointing, memory scoping, streaming, double-texting guards, LLM retry/fallback, rate limiting, PII hardening, distributed tracing, and FilesystemBackend removal.

**Architecture:** Add `user_id` as the single tenant key across all user-owned tables. Replace volatile MemorySaver with AsyncPostgresSaver. Add SSE streaming, middleware for retries/rate-limits/PII, and OpenTelemetry tracing. All changes are additive — no existing API contracts break (new header required).

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, PostgreSQL 16, LangGraph, langgraph-checkpoint-postgres, OpenTelemetry, asyncio SSE

---

## Execution Order

Gaps must be implemented in dependency order:

1. **Task 1** — Multi-tenancy (user_id) — foundational
2. **Task 2** — Memory scoping by user_id — depends on Task 1
3. **Task 3** — Persistent checkpointer — independent, follows schema changes
4. **Task 4** — FilesystemBackend removal — independent, small
5. **Task 5** — Double-texting guards — independent middleware
6. **Task 6** — LLM retry/fallback middleware — independent
7. **Task 7** — Agent-level rate limiting — independent
8. **Task 8** — PII middleware hardening — extends existing
9. **Task 9** — Streaming SSE — depends on pipeline
10. **Task 10** — Distributed tracing — cross-cutting, applied last

---

### Task 1: Multi-tenancy (user_id)

**Files:**
- Create: `backend/alembic/versions/002_add_user_id.py`
- Modify: `backend/src/db/models.py` (add user_id to Document, BulkJob, ConversationSummary, MemoryEntry)
- Modify: `backend/src/api/dependencies.py` (add get_current_user_id)
- Modify: `backend/src/db/repositories/documents.py` (accept/filter user_id)
- Modify: `backend/src/db/repositories/bulk_jobs.py` (accept/filter user_id)
- Modify: `backend/src/db/repositories/memory.py` (accept/filter user_id)
- Modify: `backend/src/services/document_service.py` (thread user_id)
- Modify: `backend/src/bulk/service.py` (thread user_id)
- Modify: All routers in `backend/src/api/routers/` (add Depends(get_current_user_id))
- Test: Update ALL existing test files to include X-User-Id header

- [ ] **Step 1: Write migration 002_add_user_id.py**

Add `user_id` (String(200), nullable=True, indexed) to `documents`, `bulk_jobs`, `conversation_summaries`, `memory_entries`. Nullable initially to not break existing data. Drop unique constraint on `conversation_summaries.session_id`, replace with composite `(user_id, session_id)`.

- [ ] **Step 2: Update ORM models**

Add `user_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)` to Document (after line 86), BulkJob (after line 250), ConversationSummary (after line 308), MemoryEntry (after line 329).

- [ ] **Step 3: Add get_current_user_id dependency**

In `backend/src/api/dependencies.py`, add:
```python
async def get_current_user_id(
    x_user_id: str | None = Header(None, alias="X-User-Id"),
) -> str:
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(status_code=401, detail="X-User-Id header required")
    return x_user_id.strip()
```

- [ ] **Step 4: Update DocumentRepository**

Add `user_id` parameter to `create()`, `get_by_id()`, `get_by_hash()`, `list_all()`, `delete()`. Filter queries with `.where(Document.user_id == user_id)` when provided.

- [ ] **Step 5: Update BulkJobRepository**

Add `user_id` parameter to `create()`, `get_by_id()`, `list_all()`.

- [ ] **Step 6: Update service layers**

Thread `user_id` through DocumentService and BulkJobService methods into repo calls.

- [ ] **Step 7: Update all API routers**

Add `user_id: str = Depends(get_current_user_id)` to every endpoint that touches user-owned data (documents, bulk, classify, extract, summarize, ingest, rag, parse). Pass to service layers.

- [ ] **Step 8: Update all existing tests**

Add `headers={"X-User-Id": "test-user"}` to all HTTP client calls in test files. Add tests for: missing header returns 401, user isolation (User A can't see User B's docs).

- [ ] **Step 9: Run migration and tests**

```bash
cd backend && alembic upgrade head && uv run pytest -x -q
```

- [ ] **Step 10: Commit**

```bash
git add -A && git commit -m "feat: add multi-tenancy with user_id across all user-owned tables"
```

---

### Task 2: Memory Scoping by user_id

**Files:**
- Modify: `backend/src/agents/memory/short_term.py`
- Modify: `backend/src/agents/memory/long_term.py`
- Modify: `backend/src/db/repositories/memory.py`
- Test: `backend/tests/test_short_term_memory.py`, `backend/tests/test_long_term_memory.py`

- [ ] **Step 1: Update ShortTermMemory**

Add `user_id: str` as first parameter to all public methods. Internal key becomes `f"{user_id}:{session_id}"`. Default `user_id="anonymous"` for backward compat during transition.

- [ ] **Step 2: Update PostgresLongTermMemory**

Add `user_id: str` to `save_conversation_summary()`, `get_conversation_summary()`. For `put()`/`get()`/`delete()`/`search()`, prefix namespace with `f"{user_id}/"`.

- [ ] **Step 3: Update ConversationSummaryRepository**

Update `upsert()` and `get_by_session()` to accept and filter by `user_id`.

- [ ] **Step 4: Update tests**

Test user isolation: User A's memory is invisible to User B in both short-term and long-term stores.

- [ ] **Step 5: Run tests and commit**

```bash
cd backend && uv run pytest -x -q tests/test_short_term_memory.py tests/test_long_term_memory.py
git commit -m "feat: scope memory stores by user_id for multi-tenant isolation"
```

---

### Task 3: Persistent Checkpointer (AsyncPostgresSaver)

**Files:**
- Modify: `backend/pyproject.toml` (add langgraph-checkpoint-postgres)
- Modify: `backend/src/config/settings.py` (add database_url_sync property)
- Modify: `backend/src/bulk/pipeline.py` (replace MemorySaver)
- Test: `backend/tests/test_bulk_pipeline.py`

- [ ] **Step 1: Add dependency**

Add `"langgraph-checkpoint-postgres>=2.0.0"` to pyproject.toml.

- [ ] **Step 2: Add sync DB URL property**

In `AppSettings`, add:
```python
@property
def database_url_sync(self) -> str:
    return self.database_url.replace("postgresql+asyncpg://", "postgresql://")
```

- [ ] **Step 3: Replace MemorySaver in pipeline.py**

Replace `MemorySaver` with `AsyncPostgresSaver.from_conn_string()`. Add `async def create_checkpointer(conn_string: str)` that calls `.setup()` to create checkpoint tables.

- [ ] **Step 4: Update run_bulk_pipeline to accept DB URL**

Pass `db_url` to pipeline builder. Create checkpointer at startup.

- [ ] **Step 5: Update tests and commit**

Mock the checkpointer in tests. Verify pipeline compiles and runs with the new type.

```bash
cd backend && uv run pytest -x -q tests/test_bulk_pipeline.py
git commit -m "feat: replace volatile MemorySaver with persistent AsyncPostgresSaver"
```

---

### Task 4: FilesystemBackend Removal

**Files:**
- Create: `backend/src/agents/backends.py` (InMemoryBackend)
- Modify: `backend/src/agents/orchestrator.py`
- Test: `backend/tests/test_orchestrator.py`

- [ ] **Step 1: Create InMemoryBackend**

```python
class InMemoryBackend:
    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
    async def read(self, key: str) -> Any: ...
    async def write(self, key: str, data: Any) -> None: ...
    async def delete(self, key: str) -> bool: ...
```

- [ ] **Step 2: Replace FilesystemBackend in orchestrator**

Replace `FilesystemBackend(root_dir="./data")` with `InMemoryBackend()`. Remove `FilesystemMiddleware` from middleware list.

- [ ] **Step 3: Test and commit**

```bash
cd backend && uv run pytest -x -q tests/test_orchestrator.py
git commit -m "refactor: replace FilesystemBackend with InMemoryBackend"
```

---

### Task 5: Double-texting Guards

**Files:**
- Create: `backend/src/api/middleware/run_guard.py`
- Modify: `backend/src/api/dependencies.py`
- Modify: `backend/src/api/routers/classify.py`, `extract.py`, `summarize.py`, `ingest.py`, `parse.py`
- Test: `backend/tests/test_run_guard.py`

- [ ] **Step 1: Create RunGuard**

```python
class RunGuard:
    def __init__(self) -> None:
        self._active: dict[str, asyncio.Event] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, resource_id: str) -> bool: ...
    async def release(self, resource_id: str) -> None: ...
```

- [ ] **Step 2: Add as FastAPI dependency**

In `dependencies.py`, add `get_run_guard()` returning a singleton RunGuard. In routers, call `acquire(doc_id)` before processing; if False, return 409 Conflict.

- [ ] **Step 3: Test concurrent access returns 409**

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: add double-texting guard to prevent concurrent doc processing"
```

---

### Task 6: LLM Retry/Fallback Middleware

**Files:**
- Create: `backend/src/agents/middleware/retry.py`
- Modify: `backend/src/config/settings.py` (add fallback_model, llm_max_retries)
- Modify: `backend/src/agents/classifier.py`, `extractor.py`, `judge.py`, `summarizer.py`
- Test: `backend/tests/test_retry_middleware.py`

- [ ] **Step 1: Create LLMRetryMiddleware**

Exponential backoff with jitter. Retries on 429, 500, 502, 503, 504. Falls back to alternate model after max retries. Passes through 400/422 immediately.

- [ ] **Step 2: Add settings**

`openai_fallback_model`, `llm_max_retries`, `llm_base_delay`.

- [ ] **Step 3: Wrap subagent LLM calls**

Each subagent's main method wraps its LLM invocation with retry middleware.

- [ ] **Step 4: Test retry behavior**

Mock LLM to return 429 twice then succeed. Test fallback activation. Test non-retryable passthrough.

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add LLM retry with exponential backoff and model fallback"
```

---

### Task 7: Agent-level Rate Limiting

**Files:**
- Create: `backend/src/agents/middleware/rate_limit.py`
- Modify: `backend/src/config/settings.py`
- Modify: `backend/src/bulk/pipeline.py` (create limiter per run)
- Test: `backend/tests/test_rate_limit.py`

- [ ] **Step 1: Create AgentRateLimiter**

Track LLM call count and tool call count per run. Raise `AgentRateLimitError` when exceeded. Configurable limits.

- [ ] **Step 2: Add settings**

`agent_max_llm_calls` (default 50), `agent_max_tool_calls` (default 200).

- [ ] **Step 3: Integrate with pipeline**

Create per-run limiter in `run_pipeline_for_document()`, pass via state.

- [ ] **Step 4: Test and commit**

```bash
git commit -m "feat: add agent-level rate limiting to prevent runaway loops"
```

---

### Task 8: PII Middleware Hardening

**Files:**
- Modify: `backend/src/agents/middleware/pii_filter.py` (add strategies, output filtering)
- Create: `backend/src/agents/middleware/pii_log_filter.py`
- Modify: `backend/src/api/app.py` (register log filter)
- Test: `backend/tests/test_pii_filter.py`

- [ ] **Step 1: Add PIIStrategy enum**

REDACT (default, existing behavior), MASK (preserve last 4 chars), BLOCK (raise PIIDetectedError).

- [ ] **Step 2: Update PIIFilterMiddleware**

Accept `strategy` in constructor. Implement mask and block strategies.

- [ ] **Step 3: Create PIILogFilter**

Logging filter that redacts PII from log record messages.

- [ ] **Step 4: Register log filter in app factory**

- [ ] **Step 5: Test all strategies and commit**

```bash
git commit -m "feat: harden PII middleware with configurable strategies and log filtering"
```

---

### Task 9: Streaming SSE

**Files:**
- Create: `backend/src/api/routers/stream.py`
- Create: `backend/src/bulk/event_bus.py`
- Modify: `backend/src/api/app.py` (register stream router)
- Modify: `backend/src/bulk/service.py` (publish events)
- Test: `backend/tests/test_stream_router.py`, `backend/tests/test_event_bus.py`

- [ ] **Step 1: Create PipelineEventBus**

In-memory pub/sub with `asyncio.Queue` per subscriber. Methods: `subscribe(job_id)`, `unsubscribe(job_id, queue)`, `publish(job_id, event)`.

- [ ] **Step 2: Create SSE stream router**

`GET /api/v1/stream/jobs/{job_id}` returns `StreamingResponse(media_type="text/event-stream")`. Async generator reads from event bus queue, formats as SSE `data: {json}\n\n`.

- [ ] **Step 3: Publish events from bulk service**

After each document node completes, publish `{node, document_id, status, timestamp}`.

- [ ] **Step 4: Register router and test**

```bash
git commit -m "feat: add SSE streaming for real-time pipeline progress"
```

---

### Task 10: Distributed Tracing (OpenTelemetry)

**Files:**
- Modify: `backend/pyproject.toml` (add otel packages)
- Modify: `backend/src/config/settings.py` (add otel settings)
- Create: `backend/src/observability/tracing.py`
- Modify: `backend/src/api/app.py` (init tracing, add correlation ID middleware)
- Modify: `backend/src/bulk/nodes.py` (add spans)
- Test: `backend/tests/test_tracing.py`

- [ ] **Step 1: Add dependencies**

`opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-exporter-otlp-proto-grpc`.

- [ ] **Step 2: Add settings**

`otel_enabled` (default False), `otel_service_name`, `otel_exporter_endpoint`.

- [ ] **Step 3: Create tracing setup module**

`init_tracing(settings)` configures TracerProvider, OTLP exporter, FastAPI instrumentor.

- [ ] **Step 4: Add correlation ID middleware**

Extract/generate `X-Correlation-Id` header, attach to current span and request state. Include in request logs.

- [ ] **Step 5: Add spans to pipeline nodes**

Wrap each node in `backend/src/bulk/nodes.py` with `tracer.start_as_current_span(node_name)`.

- [ ] **Step 6: Test tracing is no-op when disabled, spans created when enabled**

```bash
git commit -m "feat: add OpenTelemetry distributed tracing with correlation IDs"
```

---

## Verification

After all tasks complete:

1. **Migration**: `cd backend && alembic upgrade head` — no errors
2. **Tests**: `cd backend && uv run pytest -x -q` — all pass
3. **Lint**: `cd backend && uv run ruff check .` — clean
4. **Type check**: `cd backend && uv run mypy src/` — clean
5. **Manual test**: Start app, send requests with/without `X-User-Id` header, verify 401 without header
6. **Multi-user test**: Upload doc as User A, verify User B cannot see it
7. **SSE test**: Start bulk job, connect to SSE endpoint, verify events stream
