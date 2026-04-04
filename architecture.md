# PE Document Intelligence Platform — Architecture

## System Overview

A document intelligence platform for Private Equity that processes LPA and Subscription Agreement documents through a multi-step AI pipeline: upload, parse, classify, extract, summarize, ingest, and retrieve. Supports single-document and bulk processing modes with a natural language analytics dashboard.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        React Frontend (Vite, port 5173)                 │
│  Dashboard │ Upload │ Bulk │ Analytics │ Insights │ Categories │ RAG   │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ REST API + SSE
┌──────────────────────────────▼──────────────────────────────────────────┐
│                     FastAPI Backend (port 8000)                         │
│                                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────────┐  │
│  │  API Layer   │  │ Agent Layer  │  │ RAG Layer  │  │ Audit Layer  │  │
│  │ 14 routers   │  │ DeepAgents   │  │ Weaviate   │  │ Background   │  │
│  │ FastAPI deps │  │ GPT-5.4-mini │  │ Recharts   │  │ Queue + SSE  │  │
│  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘  └──────┬───────┘  │
│         │                 │                │                │           │
│  ┌──────▼─────────────────▼────────────────▼────────────────▼────────┐  │
│  │                      Service Layer                                │  │
│  │  ParseService │ ExtractionService │ SummaryService │ IngestService│  │
│  └──────────────────────────┬────────────────────────────────────────┘  │
│                              │                                          │
│  ┌──────────────────────────▼────────────────────────────────────────┐  │
│  │                    Data Layer (SQLAlchemy 2.0 + asyncpg)           │  │
│  │  Documents │ Categories │ Extraction │ Summaries │ Audit │ Bulk   │  │
│  └──────────────────────────┬────────────────────────────────────────┘  │
└──────────────────────────────┼──────────────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
   ┌──────▼──────┐     ┌──────▼──────┐     ┌──────▼──────┐
   │ PostgreSQL   │     │  Weaviate   │     │  Reducto    │
   │ 16 (Docker)  │     │  1.30       │     │  Cloud API  │
   │ port 5432    │     │  port 8080  │     │  (parsing)  │
   └──────────────┘     └─────────────┘     └─────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + Vite + TypeScript + Tailwind CSS + TanStack Query + Recharts |
| Backend | Python 3.13 + FastAPI + SQLAlchemy 2.0 + asyncpg |
| Agent Framework | DeepAgents (built on LangGraph) |
| LLMs | GPT-5.4-mini (agents), GPT-5.3-codex (analytics SQL) |
| Document Parser | Reducto Cloud API |
| Database | PostgreSQL 16 (Docker) |
| Vector Store | Weaviate 1.30 (Docker) + LangChain integration |
| Embeddings | OpenAI text-embedding-3-small |
| Re-ranker | cross-encoder/ms-marco-MiniLM-L-6-v2 (local) |
| Chunking | LangChain MarkdownHeaderTextSplitter + RecursiveCharacterTextSplitter |

---

## Document Processing Pipeline

### State Machine

```
UPLOADED → PARSED → CLASSIFIED → EXTRACTED → SUMMARIZED → INGESTED
              ↘                      ↑            ↑           ↑
           EDITED ───────────────────┘            │           │
                                                  │           │
              (re-classify and re-extract allowed from any state)
              (re-ingest allowed from any parsed state)
```

### Single Document Flow

```
1. Upload     → Validate file type/size/magic bytes, SHA-256 dedup, save to data/upload/
2. Parse      → Reducto Cloud API → markdown with tables → save to data/parsed/
3. Summarize  → PE-attribute-preserving summary (17 key attributes) → disk cache
4. Classify   → Hybrid: file name regex + content/summary LLM → confidence 0-100
5. Extract    → Dynamic Pydantic model (value + source_text per field) → disk cache + DB
6. Judge      → Field-aware confidence scoring (source text + metadata validation)
7. Ingest     → MarkdownHeaderTextSplitter → text-embedding-3-small → Weaviate
```

### Bulk Processing Flow

```
POST /bulk/upload → Create BulkJob + Documents → background_tasks.add_task()
                                                         │
                    ┌────────────────────────────────────▼────────┐
                    │  LangGraph Pipeline (10 concurrent docs)    │
                    │  parse → summarize → classify → extract →   │
                    │  ingest → finalize                          │
                    │  asyncio.Semaphore(10)                      │
                    └─────────────────────────────────────────────┘
```

---

## Agent Architecture

### Subagents

| Agent | Model | Purpose | Key Feature |
|-------|-------|---------|-------------|
| Classifier | GPT-5.4-mini | Categorize documents | Hybrid: filename regex + LLM with summary preference |
| Extractor | GPT-5.4-mini | Extract fields with source text | Dynamic Pydantic model: `{field}_value` + `{field}_source` |
| Judge | GPT-5.4-mini | Evaluate extraction confidence | Field-aware: uses data_type, required, examples metadata |
| Summarizer | GPT-5.4-mini | PE-attribute-preserving summaries | Preserves 17 key PE attributes (fees, terms, waterfall, etc.) |
| RAG Retriever | GPT-5.4-mini | Search + answer generation | Over-fetch from Weaviate → cross-encoder re-rank → LLM answer |
| Data Agent | GPT-5.3-codex | Natural language analytics | Schema introspection → SQL generation → chart config |

### PII Middleware

Applied before all LLM calls. Redacts SSN, email, phone, address, account numbers while preserving financial terms (management fee, carried interest, etc.).

---

## RAG Pipeline

```
User Query
    ↓
Weaviate Hybrid Search (fetch 5 chunks, alpha=0.5)
    ↓
Cross-encoder Re-rank (ms-marco-MiniLM-L-6-v2, return top 2)
    ↓
LLM Answer Generation (GPT-5.4-mini with section-aware context)
    ↓
Response with answer + citations (document, section, score)
```

### Chunking Strategy

Two-stage markdown-aware splitting:
1. `MarkdownHeaderTextSplitter` — splits by `#`, `##`, `###` headers, preserves section hierarchy in metadata
2. `RecursiveCharacterTextSplitter` — splits oversized sections (max 2048 chars, 400 char overlap)

Each chunk carries: `document_id`, `document_name`, `document_category`, `file_name`, `chunk_index`, `header_1`, `header_2`, `header_3`

---

## Database Schema

### 12 Tables

```
documents ──────────────┐
  │                     │
  ├── document_categories (FK: document_category_id)
  │     └── extraction_schemas
  │           └── extraction_fields
  │
  ├── extracted_values (FK: document_id, field_id)
  ├── document_summaries (FK: document_id)
  │
  ├── bulk_job_documents (FK: document_id, job_id)
  │     └── bulk_jobs
  │
  └── (implicit) audit_logs (tracks all document events)

conversation_summaries
memory_entries
```

### Key Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `documents` | Core records | id, file_name, status, document_category_id, parsed_path, parse_confidence_pct |
| `document_categories` | LPA, Subscription, Side Letter, Other | name, description, classification_criteria |
| `extraction_fields` | 8 LPA fields (fund name, GP, fees, etc.) | field_name, display_name, data_type, required |
| `extracted_values` | Per-document per-field values | extracted_value, source_text, confidence, requires_review |
| `audit_logs` | System activity tracking | event_type, entity_type, document_id, details (JSONB) |
| `bulk_jobs` | Batch processing | status, total_documents, processed_count, failed_count |

---

## Caching Strategy

Dual storage (DB + disk) with content-hash invalidation:

```
data/
  upload/          # original files
  parsed/          # parsed markdown ({filename}.md)
  summary/         # summary cache ({doc_id}.json) — content_hash based
  extraction/      # extraction cache ({doc_id}.json) — content_hash based
```

- Classify/extract/summarize endpoints return cached results without LLM calls
- `force=true` query parameter bypasses cache
- Re-ingestion deletes old Weaviate chunks before inserting new ones

---

## Audit & Observability

### Audit Framework

```
Request Thread                    Background Audit Thread
│                                 │
├─ emit_audit_event()             ├─ asyncio event loop (dedicated thread)
│  (non-blocking, fire-and-forget)│  ├─ Write to audit_logs table (own DB pool: 2+1)
│                                 │  └─ Broadcast to SSE subscribers
```

### Tracked Events

| Event | Trigger |
|-------|---------|
| `document.uploaded` | File upload |
| `document.parsed` | Reducto parse complete |
| `document.classified` | Classification complete |
| `document.extracted` | Extraction + judge complete |
| `document.summarized` | Summary generated |
| `document.ingested` | Chunks stored in Weaviate |
| `document.deleted` | Document removed |
| `bulk.job_created` | Bulk upload started |
| `bulk.job_completed` / `bulk.job_failed` | Bulk pipeline finished |
| `rag.query` | RAG search (includes query, answer, citations) |
| `analytics.query` | Data agent query (includes SQL, row count) |

### Real-time SSE

```
GET /api/v1/events/stream → EventSource → invalidate TanStack Query caches
```

Each audit event broadcasts to SSE subscribers. Frontend maps event types to query keys for selective cache invalidation. Auto-reconnect on disconnect.

---

## Analytics Dashboard

Natural language queries over the application database:

```
"How many documents are in each status?"
    ↓
Data Agent (GPT-5.3-codex) + Schema Introspection
    ↓
SQL: SELECT status, COUNT(*) as count FROM documents GROUP BY status
    ↓
Chart Config: { type: "bar", xKey: "status", yKey: "count" }
    ↓
Recharts rendering (bar, line, pie, table)
```

Safety: read-only (blocked DDL/DML), auto-LIMIT 1000, 10s timeout.

---

## API Endpoints

### Document Pipeline

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/documents/upload` | Upload document |
| GET | `/api/v1/documents` | List documents (with category name) |
| DELETE | `/api/v1/documents/:id` | Delete document |
| POST | `/api/v1/parse/:id` | Parse via Reducto |
| POST | `/api/v1/classify/:id` | Classify (cached unless force=true) |
| POST | `/api/v1/extract/:id` | Extract fields (cached unless force=true) |
| POST | `/api/v1/summarize/:id` | Summarize (cached) |
| POST | `/api/v1/ingest/:id` | Ingest to Weaviate |

### RAG & Analytics

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/rag/query` | RAG search with re-ranking |
| POST | `/api/v1/analytics/query` | NL-to-SQL analytics |
| GET | `/api/v1/events/stream` | SSE real-time events |
| GET | `/api/v1/audit/trail` | Query audit logs |

### Bulk Processing

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/bulk/upload` | Upload + start pipeline |
| GET | `/api/v1/bulk/jobs` | List jobs |
| GET | `/api/v1/bulk/jobs/:id` | Job details with per-doc status |

### Configuration

| Method | Path | Purpose |
|--------|------|---------|
| GET/POST/PUT/DELETE | `/api/v1/config/categories` | CRUD categories |
| GET/POST | `/api/v1/config/categories/:id/fields` | Extraction fields |

---

## Frontend Architecture

### Navigation

```
Dashboard          — Card/table view, action icons, inline detail panel
Upload             — Single file upload with drag-drop
Bulk Processing    — Multi-file upload, select, process, job tracking
─────────────────
ADMIN
  Categories       — Inline editable category management
  Extraction Fields — Inline editable field table per category
─────────────────
MANAGEMENT
  Analytics        — NL-to-SQL dashboard with Recharts
  Insights         — Audit trail, activity timeline, stat cards
```

### State Management

- **TanStack Query** — all server state, selective cache invalidation via SSE
- **SSE EventSource** — real-time updates, auto-reconnect
- **No polling** — pure push architecture

### Key Components

| Component | Purpose |
|-----------|---------|
| DocumentCardGrid / DocumentRow | Card and table views with action icons |
| DocumentDetailPanel | Inline extraction results + summary + parsed content |
| DocumentTreePanel | Document selection + RAG search interface |
| ExtractionFieldEditor | Inline editable field table |
| CategoryManager + CategoryForm | Inline category CRUD |
| BulkUploadZone | Drag-drop with file selection |
| InsightsPage | Stat cards + activity timeline with filters |
| AnalyticsPage | NL search → Recharts (bar, line, pie, table) |

---

## Configuration

### Environment Variables (.env)

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `REDUCTO_API_KEY` | Reducto parsing service key |
| `REDUCTO_BASE_URL` | Reducto API endpoint |
| `DATABASE_URL` | PostgreSQL async connection string |
| `WEAVIATE_URL` | Weaviate server URL |
| `OPENAI_MODEL` | Default LLM model |
| `DB_POOL_SIZE` | Main DB pool size (default: 5) |
| `DB_MAX_OVERFLOW` | Main DB overflow (default: 5) |
| `AUDIT_POOL_SIZE` | Audit DB pool size (default: 2) |
| `AUDIT_MAX_OVERFLOW` | Audit DB overflow (default: 1) |

### config.yml

```yaml
storage:
  upload_dir: "./data/upload"
  parsed_dir: "./data/parsed"
  summary_dir: "./data/summary"
  extraction_dir: "./data/extraction"

chunking:
  max_tokens: 512
  overlap_tokens: 100

bulk:
  concurrent_documents: 3

rag:
  default_search_mode: "hybrid"
  default_alpha: 0.5
  top_k: 5
```

---

## Infrastructure

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:16-alpine
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]

  weaviate:
    image: semitechnologies/weaviate:1.30.0
    ports: ["8080:8080", "50051:50051"]
    environment:
      DEFAULT_VECTORIZER_MODULE: text2vec-openai
      ENABLE_MODULES: text2vec-openai
```

### Running

```bash
# Infrastructure
docker compose up -d

# Backend
cd backend && uv run uvicorn src.main:app --port 8000

# Frontend
cd frontend && npm run dev
```

---

## Project Structure

```
document_intelligence_adv_v2/
├── backend/
│   ├── src/
│   │   ├── agents/            # AI subagents (classifier, extractor, judge, summarizer, RAG)
│   │   │   ├── middleware/    # PII filter, retry, rate limiting
│   │   │   ├── schemas/      # Pydantic models for agent responses
│   │   │   └── memory/       # Short-term and long-term memory
│   │   ├── api/
│   │   │   ├── routers/      # 14 FastAPI routers
│   │   │   ├── schemas/      # Request/response Pydantic models
│   │   │   ├── middleware/    # Run guard, rate limiting
│   │   │   └── dependencies.py
│   │   ├── audit/             # Background audit queue + SSE broadcast
│   │   ├── bulk/              # LangGraph pipeline (10-doc concurrency)
│   │   ├── data_agent/        # NL-to-SQL analytics agent
│   │   ├── db/
│   │   │   ├── models/        # 12 ORM models
│   │   │   ├── repositories/  # Async CRUD with eager loading
│   │   │   └── connection.py  # Engine + session factory
│   │   ├── rag/               # Weaviate client, chunker, re-ranker
│   │   ├── services/          # Business logic (parse, extract, ingest, summarize)
│   │   ├── config/            # Pydantic settings (.env + config.yml)
│   │   ├── parser/            # Reducto client
│   │   └── storage/           # Local file storage
│   ├── data/                  # upload/, parsed/, summary/, extraction/
│   ├── alembic/               # DB migrations
│   └── config.yml
├── frontend/
│   ├── src/
│   │   ├── components/        # UI components (documents, config, bulk, parse, ui)
│   │   ├── hooks/             # TanStack Query hooks + SSE EventSource
│   │   ├── lib/api/           # Axios API clients with case transformation
│   │   ├── pages/             # 12 page components
│   │   └── types/             # TypeScript interfaces
│   └── package.json
├── docker-compose.yml
├── architecture.md
└── docs/
```
