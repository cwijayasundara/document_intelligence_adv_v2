# System Design — PE Document Intelligence Platform

**Version:** 1.0
**Date:** 2026-03-28

---

## 1. High-Level Architecture

```
+---------------------+         +-------------------------------+
|                     |  HTTP   |                               |
|  React 19 SPA       +-------->+  FastAPI Backend (port 8000)   |
|  Vite (port 5173)   |  REST   |                               |
|  TypeScript          |         |  +---------------------------+ |
|  Tailwind CSS 4      |         |  | API Layer (Routers)       | |
|  TanStack Query      |         |  |  documents, parse,        | |
|  TipTap Editor       |         |  |  classify, extract,       | |
|  Axios               |         |  |  summarize, ingest,       | |
+---------------------+         |  |  rag, config, bulk,       | |
                                 |  |  health                   | |
                                 |  +---------------------------+ |
                                 |              |                 |
                                 |  +-----------v-----------+    |
                                 |  | Service Layer          |    |
                                 |  |                        |    |
                                 |  | +--------------------+ |    |
                                 |  | | DeepAgent          | |    |
                                 |  | | Orchestrator       | |    |
                                 |  | |                    | |    |
                                 |  | | Subagents:         | |    |
                                 |  | |  - Classifier      | |    |
                                 |  | |  - Extractor       | |    |
                                 |  | |  - Judge           | |    |
                                 |  | |  - Summarizer      | |    |
                                 |  | |  - RAG Retriever   | |    |
                                 |  | |                    | |    |
                                 |  | | Middleware:         | |    |
                                 |  | |  - PII Filter      | |    |
                                 |  | |  - Filesystem      | |    |
                                 |  | |  - SubAgent        | |    |
                                 |  | |  - Summarization   | |    |
                                 |  | +--------------------+ |    |
                                 |  |                        |    |
                                 |  | +--------------------+ |    |
                                 |  | | LangGraph Bulk     | |    |
                                 |  | | StateGraph Pipeline| |    |
                                 |  | | (10 concurrent)    | |    |
                                 |  | +--------------------+ |    |
                                 |  |                        |    |
                                 |  | +--------------------+ |    |
                                 |  | | Memory Layer       | |    |
                                 |  | |  - ShortTermMemory | |    |
                                 |  | |    (in-memory LRU) | |    |
                                 |  | |  - LongTermMemory  | |    |
                                 |  | |    (PostgreSQL)    | |    |
                                 |  | +--------------------+ |    |
                                 |  +-----------+-----------+    |
                                 |              |                 |
                                 |  +-----------v-----------+    |
                                 |  | Repository Layer       |    |
                                 |  | SQLAlchemy 2.0 async   |    |
                                 |  | asyncpg driver         |    |
                                 |  +--+--------+--------+--+    |
                                 +-----|--------|--------|--------+
                                       |        |        |
                               +-------v-+  +---v----+  +v-----------+
                               |Reducto   |  |Postgres|  |Weaviate    |
                               |Cloud API |  |16      |  |Hybrid      |
                               |(parsing) |  |(Docker)|  |Search      |
                               +----------+  |:5432   |  |(Docker)    |
                                             +--------+  |:8080       |
                                                         +------------+
                               +----------+
                               |OpenAI API|
                               |GPT-5.4-  |
                               |mini      |
                               +----------+
```

---

## 2. Component Inventory

### 2.1 Frontend (React SPA)

| Component | Technology | Responsibility |
|-----------|-----------|----------------|
| App Shell | React 19, React Router | Routing, layout, navigation |
| API Client | Axios | HTTP calls with case transformation |
| Server State | TanStack Query | Cache, polling, optimistic updates |
| Rich Editor | TipTap (StarterKit + Table) | Parsed content editing |
| File Upload | react-dropzone | Drag-drop single and bulk upload |
| Design System | Tailwind CSS 4 | Tokens, typography, color palettes |

### 2.2 Backend (FastAPI)

| Component | Technology | Responsibility |
|-----------|-----------|----------------|
| API Routers | FastAPI | REST endpoints, request validation |
| Pydantic Schemas | Pydantic v2 | Request/response serialization |
| ORM Models | SQLAlchemy 2.0 | Database table definitions |
| Repositories | SQLAlchemy async sessions | CRUD operations |
| State Machine | Custom service | Document status transitions |
| Config Loader | PyYAML + Pydantic | config.yml + .env loading |

### 2.3 Agent Framework

| Component | Technology | Responsibility |
|-----------|-----------|----------------|
| Orchestrator | DeepAgents 0.4.12 create_deep_agent | Central agent with tool access and subagent delegation |
| Classifier | DeepAgents subagent | Document category detection |
| Extractor | DeepAgents subagent | Schema-driven field extraction with dynamic Pydantic models |
| Judge | DeepAgents subagent | Confidence scoring per extracted field |
| Summarizer | DeepAgents subagent | Document summary generation |
| RAG Retriever | DeepAgents subagent | Weaviate hybrid search + answer synthesis |
| PII Middleware | DeepAgents pre-model callback | Redacts PII before LLM calls |
| Bulk Pipeline | LangGraph StateGraph | 7-node pipeline with concurrent execution |

### 2.4 External Services

| Service | Purpose | Connection |
|---------|---------|------------|
| Reducto Cloud API | PDF/DOCX/XLSX/image to markdown | HTTPS, API key |
| OpenAI API (GPT-5.4-mini) | LLM for all agent operations | HTTPS, API key |
| OpenAI Embeddings | Vector embeddings via Weaviate text2vec-openai | Via Weaviate module |
| PostgreSQL 16 | Structured data, long-term memory | Docker, port 5432 |
| Weaviate | Vector store, hybrid search | Docker, port 8080 |

---

## 3. Data Flow

### 3.1 Single-Document Flow

```
User uploads file
    |
    v
[POST /documents/upload]
    |-- Save file to data/upload/
    |-- SHA-256 hash for dedup
    |-- Create document record (status=uploaded)
    |
    v
[POST /parse/:id]
    |-- Send file to Reducto Cloud API
    |-- Receive markdown
    |-- Save to data/parsed/{id}.md
    |-- Update status=parsed
    |
    v
[PUT /parse/:id/content]  (optional)
    |-- User edits in TipTap
    |-- Save edited markdown
    |-- Update status=edited
    |
    v
[POST /classify/:id]
    |-- PII middleware redacts content
    |-- Classifier subagent: parsed content + all categories -> best match
    |-- Save document_category_id
    |-- Update status=classified
    |
    v
[POST /extract/:id]
    |-- Load extraction schema for category
    |-- Build dynamic Pydantic model
    |-- PII middleware redacts content
    |-- Extractor subagent: extract fields with source text
    |-- Judge subagent: evaluate confidence per field
    |-- Save to extracted_values table
    |-- User reviews low-confidence fields (hard gate)
    |-- Update status=extracted (after review complete)
    |
    v
[POST /summarize/:id]
    |-- PII middleware redacts content
    |-- Summarizer subagent: generate summary + key topics
    |-- Save to document_summaries with content_hash
    |-- Update status=summarized
    |
    v
[POST /ingest/:id]
    |-- SemanticChunker splits parsed markdown
    |-- Upsert chunks to Weaviate with metadata
    |-- Update status=ingested
    |
    v
[POST /rag/query]
    |-- User enters query with scope/mode
    |-- RAG retriever: Weaviate hybrid search
    |-- Synthesize answer with citations
    |-- Return to user
```

### 3.2 Bulk Processing Flow

```
[POST /bulk/upload]
    |-- Accept multiple files
    |-- Create bulk_job (status=pending)
    |-- Create bulk_job_documents per file
    |-- Create document records per file
    |-- Launch LangGraph StateGraph in background
    |
    v
LangGraph Pipeline (up to 10 concurrent documents):
    |
    parse_node ──> classify_node ──> extract_node ──> judge_node
                                                         |
                                                         v
                                          summarize_node ──> ingest_node ──> finalize_node
    |
    |-- Each node calls same subagent functions as single-doc flow
    |-- Per-document error isolation (failure does not block others)
    |-- MemorySaver checkpointing for resumability
    |-- No edit step (fully automated)
    |
    v
[GET /bulk/jobs/:id]  (frontend polls every 5s)
    |-- Returns job status + per-document progress
```

---

## 4. Infrastructure Topology

```
Developer Workstation (macOS / Linux)
|
+-- Local Processes
|   +-- Backend:  uvicorn src.main:app --reload --port 8000
|   +-- Frontend: npx vite --port 5173
|
+-- Docker Compose
|   +-- postgres:16       (port 5432, volume: pgdata)
|   +-- weaviate:latest   (port 8080, port 50051 gRPC)
|       +-- text2vec-openai module enabled
|       +-- Anonymous access enabled
|
+-- Local Filesystem
|   +-- data/upload/      (original uploaded files)
|   +-- data/parsed/      (parsed markdown files)
|   +-- data/schemas/     (YAML extraction schemas)
|
+-- External APIs (HTTPS)
    +-- Reducto Cloud API  (document parsing)
    +-- OpenAI API         (LLM + embeddings)
```

---

## 5. DeepAgents Orchestrator Design

### 5.1 Orchestrator Configuration

```python
orchestrator = create_deep_agent(
    model="openai:gpt-5.4-mini",
    tools=[parse_document, save_document, get_document_status],
    subagents=[classifier, extractor, judge, summarizer, rag_retriever],
    system_prompt="You are a PE document intelligence agent...",
    middleware=[
        FilesystemMiddleware,
        SubAgentMiddleware,
        SummarizationMiddleware,
        PIIFilterMiddleware,  # custom pre-model callback
    ],
    backend=FilesystemBackend(root="./data")
)
```

### 5.2 Subagent Definitions

| Subagent | Model | Tools | Structured Output |
|----------|-------|-------|-------------------|
| Classifier | GPT-5.4-mini | get_categories, get_parsed_content | ClassificationResult(category_id, category_name, reasoning) |
| Extractor | GPT-5.4-mini | get_extraction_schema, get_parsed_content | ExtractionResult(fields: list[ExtractedField]) |
| Judge | GPT-5.4-mini | get_extracted_values, get_parsed_content | JudgeResult(evaluations: list[FieldEvaluation]) |
| Summarizer | GPT-5.4-mini | get_parsed_content | SummaryResult(summary, key_topics) |
| RAG Retriever | GPT-5.4-mini | weaviate_hybrid_search | Free-form text with citations |

### 5.3 PII Middleware Pipeline

```
User content (with PII)
    |
    v
[PIIFilterMiddleware - pre-model callback]
    |-- Regex detection:
    |     SSN: \d{3}-\d{2}-\d{4}             -> [REDACTED_SSN]
    |     Phone: various US formats            -> [REDACTED_PHONE]
    |     Email: standard email pattern        -> [REDACTED_EMAIL]
    |     Address: US street address patterns  -> [REDACTED_ADDRESS]
    |     Bank account/routing numbers         -> [REDACTED_ACCOUNT]
    |
    |-- Pass-through (not redacted):
    |     Fund names, management fees, carried interest,
    |     preferred return, fund term, commitment period
    |
    v
Redacted content -> LLM call
    |
    v
LLM response (references [REDACTED_*] tokens)
```

### 5.4 Memory Architecture

```
+----------------------------------+
| ShortTermMemory                  |
| (in-memory LRU per session)      |
|                                  |
| - Per session_id message list    |
| - Max 20 messages, LRU trim     |
| - Used for RAG chat multi-turn  |
| - Volatile (lost on restart)    |
+----------------------------------+

+----------------------------------+
| PostgresLongTermMemory           |
| (DB-backed, persistent)          |
|                                  |
| conversation_summaries table:    |
|   session_id, agent_type,        |
|   summary, key_topics,           |
|   documents_discussed            |
|                                  |
| memory_entries table:            |
|   namespace, key, data (JSONB)   |
|   General key-value store        |
+----------------------------------+
```

---

## 6. LangGraph Bulk Pipeline Design

```
                    +-------------------+
                    | BulkPipelineState |
                    | (TypedDict)       |
                    +-------------------+
                    | document_id       |
                    | status            |
                    | parsed_content    |
                    | classification    |
                    | extraction_results|
                    | judge_results     |
                    | summary           |
                    | error             |
                    | timing_metrics    |
                    +--------+----------+
                             |
    +--------+--------+------+------+--------+--------+--------+
    |        |        |             |        |        |        |
    v        v        v             v        v        v        v
+------+ +--------+ +-------+ +-------+ +--------+ +------+ +--------+
|parse | |classify| |extract| |judge  | |summar- | |ingest| |finalize|
|_node | |_node   | |_node  | |_node  | |ize_node| |_node | |_node   |
+------+ +--------+ +-------+ +-------+ +--------+ +------+ +--------+
    |        |        |             |        |        |        |
    +--------+--------+------+------+--------+--------+--------+
                             |
                    Uses same subagent functions
                    as single-doc flow

Concurrency: asyncio.Semaphore(10)
Checkpointing: MemorySaver
Error handling: per-document isolation
```

---

## 7. Key Design Decisions

### 7.1 DeepAgents over Direct OpenAI Calls

**Decision:** Use DeepAgents 0.4.12 framework for all LLM interactions.

**Rationale:** PII middleware as a pre-model callback ensures no sensitive data leaks to the LLM regardless of which agent path executes. Subagent delegation, built-in checkpointing, and memory support reduce boilerplate. The Judge subagent being separate from the Extractor ensures evaluation objectivity.

### 7.2 Weaviate over pgvector

**Decision:** Weaviate with hybrid search (BM25 + vector) for RAG.

**Rationale:** Native hybrid search combines keyword precision (BM25) with semantic recall (vector), which is critical for legal documents where exact terminology matters. The text2vec-openai module handles embedding generation server-side, reducing backend complexity. The alpha parameter gives users control over search behavior.

### 7.3 Reducto over LlamaParse

**Decision:** Reducto Cloud API for document parsing.

**Rationale:** Cloud-hosted service requiring no local GPU resources. Supports PDF, DOCX, XLSX, and images with table structure preservation. Markdown output integrates cleanly with TipTap editor and LLM context windows.

### 7.4 Local Dev Servers + Docker Only for Databases

**Decision:** Run backend (uvicorn) and frontend (vite) natively; Docker Compose only for PostgreSQL and Weaviate.

**Rationale:** R&D project optimized for fast iteration. Hot reload on both backend (uvicorn --reload) and frontend (vite HMR) without Docker rebuild cycles. Database services benefit from Docker for consistent environments and easy teardown.

### 7.5 Repository Pattern with SQLAlchemy 2.0 Async

**Decision:** Repository classes wrapping SQLAlchemy async sessions.

**Rationale:** Decouples database operations from API handlers and agent tools. Enables clean dependency injection, testability with mock repositories, and consistent transaction management.

### 7.6 Separate Extractor and Judge Agents

**Decision:** Two separate LLM calls for extraction and confidence judging.

**Rationale:** A single model that extracts and self-evaluates tends to overrate its own confidence. By using a separate Judge subagent with fresh context, confidence scores are more reliable. The Judge can identify contradictions and ambiguities that the Extractor may have overlooked.

### 7.7 Hard Review Gate on Low-Confidence Extractions

**Decision:** Documents cannot proceed past "extracted" status until all low-confidence fields are manually reviewed.

**Rationale:** The platform's core value proposition is accuracy. Allowing unreviewed low-confidence data downstream would undermine trust. The gate ensures human oversight where it matters most while allowing high-confidence fields to flow through untouched.

### 7.8 LangGraph for Bulk Pipeline

**Decision:** LangGraph StateGraph (not raw asyncio) for bulk processing.

**Rationale:** StateGraph provides node-level checkpointing via MemorySaver, enabling pipeline resumability on failure. The graph abstraction makes the pipeline testable node-by-node. Concurrent execution is managed with asyncio.Semaphore(10) for rate limiting.

---

## 8. Error Handling Strategy

| Layer | Strategy |
|-------|----------|
| API | FastAPI exception handlers return structured JSON: {detail, error_code, context} |
| Reducto | Retry 3x with exponential backoff; on final failure, document stays in UPLOADED state |
| LLM calls | DeepAgents built-in retry (3x with backoff); on final failure, surface error to user |
| State machine | Invalid transitions return HTTP 400 with current state and valid transitions |
| Extraction review | Hard gate returns HTTP 400 with list of unreviewed field IDs |
| Bulk pipeline | Per-document error isolation; failed docs logged to bulk_job_documents.error_message |
| Weaviate | Connection retry on startup; ingestion failures leave document in SUMMARIZED state |

---

## 9. Security Considerations

- **PII never sent to LLM:** DeepAgents pre-model callback redacts before any API call
- **No authentication:** Single-user R&D platform, localhost only
- **API keys in .env:** Never committed to version control
- **Local filesystem storage:** No cloud storage; documents stay on the developer machine
- **Weaviate anonymous access:** Acceptable for local Docker instance
- **CORS:** Configured for localhost:5173 only
