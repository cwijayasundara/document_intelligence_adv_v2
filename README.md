# PE Document Intelligence Platform

Automates processing of Private Equity LPA and Subscription Agreement documents through a multi-step workflow: upload, parse, edit, classify, extract, summarize, ingest, and retrieve. Replaces manual document review with LLM-powered agents for classification, structured extraction with confidence scoring, and RAG-based retrieval.

## Architecture

```
React (Vite, :5173) ──> FastAPI Backend (:8000)
                              |
                              ├── DeepAgent Orchestrator
                              |   ├── Classifier Subagent
                              |   ├── Extractor Subagent
                              |   ├── Judge Subagent
                              |   ├── Summarizer Subagent
                              |   └── RAG Retriever Subagent
                              |
                              ├── Bulk Pipeline (LangGraph)
                              |   parse → classify → extract → judge → summarize → ingest
                              |
                              ├── Reducto API (document parsing)
                              ├── PostgreSQL 16 (:5432)
                              └── Weaviate (:8080, hybrid search)
```

**Layers:** UI → API → Service → Repository → Database (one-way dependencies)

## Tech Stack


| Component       | Technology                                                     |
| --------------- | -------------------------------------------------------------- |
| Backend         | Python 3.13, FastAPI, SQLAlchemy 2.0 (async), asyncpg, Alembic |
| Frontend        | React 19, Vite, TypeScript, Tailwind CSS 4, TanStack Query     |
| Agent Framework | DeepAgents 0.4.12 (LangGraph), OpenAI GPT-5.4-mini             |
| Document Parser | Reducto Cloud API                                              |
| Database        | PostgreSQL 16                                                  |
| Vector Store    | Weaviate (hybrid search: BM25 + vector)                        |
| Chunking        | LangChain SemanticChunker                                      |
| Testing         | pytest (backend), Vitest (frontend)                            |


## Prerequisites

- Python 3.13+
- Node.js 20+
- Docker + Docker Compose
- [uv](https://docs.astral.sh/uv/) package manager
- API keys: OpenAI, Reducto (see `.env.example`)

## Quick Start

```bash
# 1. Clone and enter
git clone <repo-url> && cd document_intelligence_adv_v2

# 2. Copy environment config
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

# 3. Start infrastructure (PostgreSQL + Weaviate)
docker compose up -d

# 4. Install backend dependencies
cd backend && uv sync && cd ..

# 5. Run database migrations
cd backend && uv run alembic upgrade head && cd ..

# 6. Start backend
cd backend && uv run uvicorn src.main:app --reload --port 8000 &

# 7. Install and start frontend
cd frontend && npm ci && npm run dev &

# 8. Verify
curl http://localhost:8000/api/v1/health
# → {"status": "healthy"}
```

Or use the bootstrap script:

```bash
bash init.sh
```

## API Endpoints


| Method | Path                                   | Description                       |
| ------ | -------------------------------------- | --------------------------------- |
| GET    | `/api/v1/health`                       | Health check                      |
| POST   | `/api/v1/documents/upload`             | Upload single document            |
| GET    | `/api/v1/documents`                    | List all documents                |
| GET    | `/api/v1/documents/:id`                | Get document details              |
| DELETE | `/api/v1/documents/:id`                | Delete document                   |
| POST   | `/api/v1/parse/:id`                    | Parse document via Reducto        |
| GET    | `/api/v1/parse/:id/content`            | Get parsed markdown               |
| PUT    | `/api/v1/parse/:id/content`            | Save edited content               |
| POST   | `/api/v1/classify/:id`                 | Classify document                 |
| POST   | `/api/v1/extract/:id`                  | Extract fields + judge confidence |
| GET    | `/api/v1/extract/:id/results`          | Get extraction results            |
| PUT    | `/api/v1/extract/:id/results`          | Update/review extracted values    |
| POST   | `/api/v1/summarize/:id`                | Generate summary                  |
| GET    | `/api/v1/summarize/:id`                | Get existing summary              |
| POST   | `/api/v1/ingest/:id`                   | Ingest into Weaviate              |
| POST   | `/api/v1/rag/query`                    | RAG query with scope filtering    |
| GET    | `/api/v1/config/categories`            | List categories                   |
| POST   | `/api/v1/config/categories`            | Create category                   |
| PUT    | `/api/v1/config/categories/:id`        | Update category                   |
| DELETE | `/api/v1/config/categories/:id`        | Delete category                   |
| GET    | `/api/v1/config/categories/:id/fields` | List extraction fields            |
| POST   | `/api/v1/config/categories/:id/fields` | Create/update fields              |
| POST   | `/api/v1/bulk/upload`                  | Start bulk processing job         |
| GET    | `/api/v1/bulk/jobs`                    | List bulk jobs                    |
| GET    | `/api/v1/bulk/jobs/:id`                | Get job details                   |


## Project Structure

```
backend/
├── src/
│   ├── api/                    # FastAPI routers and schemas
│   │   ├── routers/            # Route handlers (documents, parse, classify, etc.)
│   │   └── schemas/            # Pydantic request/response models
│   ├── agents/                 # DeepAgent subagents
│   │   ├── classifier.py       # Document classification
│   │   ├── extractor.py        # Structured field extraction
│   │   ├── judge.py            # Confidence scoring
│   │   ├── summarizer.py       # Document summarization
│   │   ├── rag_retriever.py    # RAG-based retrieval
│   │   ├── middleware/         # PII filtering middleware
│   │   └── memory/             # Short-term + long-term memory
│   ├── bulk/                   # LangGraph bulk processing pipeline
│   ├── db/                     # SQLAlchemy models, connection, repositories
│   ├── parser/                 # Reducto API client
│   ├── rag/                    # Weaviate client, chunker, ingestion
│   ├── services/               # Business logic layer
│   ├── storage/                # Local filesystem operations
│   └── config/                 # Pydantic settings (config.yml + .env)
├── tests/                      # 511 pytest tests
├── alembic/                    # Database migrations
└── config.yml                  # Application configuration

frontend/
├── src/
│   ├── pages/                  # 10 route pages
│   ├── components/             # UI components by domain
│   │   ├── documents/          # Document list, status badges
│   │   ├── upload/             # Drag-drop upload
│   │   ├── parse/              # Split view editor
│   │   ├── classify/           # Classification result + override
│   │   ├── extraction/         # 3-column extraction table
│   │   ├── summary/            # Summary display + topics
│   │   ├── chat/               # RAG chat interface
│   │   ├── config/             # Category + field management
│   │   ├── bulk/               # Bulk job dashboard
│   │   └── ui/                 # Shared UI components
│   ├── hooks/                  # TanStack Query hooks
│   ├── lib/api/                # Axios API client functions
│   └── types/                  # TypeScript type definitions
└── tailwind.config.ts          # Design tokens
```

## Testing

The platform has four independent test layers. Running all four gives high confidence the app is healthy.

### 1. Unit tests

```bash
# Backend — pytest (511 tests, 97% coverage)
cd backend && uv run pytest -x -q
cd backend && uv run pytest --cov=src --cov-report=term-missing

# Frontend — Vitest
cd frontend && npm test
```

Lint + type check:

```bash
cd backend && uv run ruff check .
cd backend && uv run mypy src/
cd frontend && npx tsc --noEmit
```

### 2. Checkpointer package tests

The `langgraph-checkpoint-asyncpg/` sibling package ships its own test suite, backed by a real PostgreSQL container via `testcontainers`. Requires Docker.

```bash
cd langgraph-checkpoint-asyncpg
uv sync --all-extras
chflags nohidden .venv/lib/python*/site-packages/*.pth 2>/dev/null   # macOS only, see note below
uv run pytest
```

Covers migrations (cold-start, idempotent rerun, resume-from-partial), saver round-trip with real JSONB/BYTEA, and schema compatibility with the upstream `langgraph-checkpoint-postgres` layout.

### 3. End-to-end checkpointer verification against your dev DB

Confirms the asyncpg-backed LangGraph checkpointer writes durable state that survives a process restart — the key behavior change versus the old `MemorySaver`.

```bash
# Start PostgreSQL (from repo root)
docker compose up -d postgres

cd backend
uv sync
chflags nohidden .venv/lib/python3.13/site-packages/*.pth 2>/dev/null   # macOS only
uv run alembic upgrade head
```

Then run the two scripts in [`backend/README.md` → "Pipeline Checkpointer → Testing the pipeline with the new checkpointer"](backend/README.md#testing-the-pipeline-with-the-new-checkpointer) — a one-shot smoke test (imports + schema at v9) and an end-to-end interrupt / resume across saver instances.

Verify no LGPL dep remains:

```bash
cd backend
uv pip list | grep -i psycopg          # no output
uv pip list | grep langgraph-checkpoint
# langgraph-checkpoint           2.x.y  (MIT)
# langgraph-checkpoint-asyncpg   0.1.0  (Apache-2.0, local editable)
```

### 4. Manual app smoke test

Exercises the full stack: upload → pipeline → review → RAG.

```bash
# Start the full stack
docker compose up -d postgres weaviate
cd backend && uv run alembic upgrade head && uv run uvicorn src.main:app --port 8000 &
cd frontend && npm run dev &

# Health
curl http://localhost:8000/api/v1/health
# → {"status": "healthy"}

# Upload a sample doc (starts the pipeline)
curl -F 'file=@docs/LPA_Horizon_Equity_Partners_IV.pdf' \
     http://localhost:8000/api/v1/documents/upload

# Get the document id from the response, then watch pipeline progress:
curl http://localhost:8000/api/v1/pipeline/<doc-id>/status

# Restart the backend mid-pipeline (kill the uvicorn process and restart it).
# Hit /status again — next_nodes and node_statuses persist across the restart.
# That's the asyncpg checkpointer doing its job; MemorySaver would have lost them.
```

Then open the UI at http://localhost:5173, upload a document, and walk through the classify / extract / summarize / chat flow.

### macOS + Python 3.13 gotcha

uv marks editable-install `.pth` files as "hidden" on macOS, and Python 3.13 silently skips hidden `.pth` files — so after `uv sync`, `import langgraph_checkpoint_asyncpg` fails with `ModuleNotFoundError`. Fix:

```bash
chflags nohidden .venv/lib/python*/site-packages/*.pth
```

Rerun after any `uv sync` / `uv add` that rewrites the `.pth` file. Linux and CI are unaffected.

## Environment Variables


| Variable          | Description                                | Required | Example                                                                 |
| ----------------- | ------------------------------------------ | -------- | ----------------------------------------------------------------------- |
| `OPENAI_API_KEY`  | OpenAI API key for LLM calls               | Yes      | `sk-...`                                                                |
| `REDUCTO_API_KEY` | Reducto Cloud API key for document parsing | Yes      | `...`                                                                   |
| `DATABASE_URL`    | PostgreSQL async connection string         | Yes      | see `.env.example` (format: `postgresql+asyncpg` scheme)                |
| `WEAVIATE_URL`    | Weaviate instance URL                      | Yes      | `http://localhost:8080`                                                 |
| `OPENAI_MODEL`    | OpenAI model to use                        | Yes      | `gpt-5.4-mini`                                                          |


## Development

**Adding a new API endpoint:**

1. Create schema in `backend/src/api/schemas/`
2. Create router in `backend/src/api/routers/`
3. Register router in `backend/src/api/app.py`
4. Add tests in `backend/tests/`

**Running without Docker (database only):**

```bash
# Start just PostgreSQL and Weaviate
docker compose up -d postgres weaviate

# Run backend directly
cd backend && uv run uvicorn src.main:app --port 8000

# Run frontend directly
cd frontend && npm run dev
```

**Configuration:** Edit `backend/config.yml` for storage paths, chunking parameters, bulk concurrency, and RAG defaults.