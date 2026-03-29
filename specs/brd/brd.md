# Business Requirements Document — PE Document Intelligence Platform

**Version:** 1.0
**Date:** 2026-03-28
**Status:** Draft — Pending Approval

---

## 1. Executive Summary

A document intelligence platform for a private equity client that automates the processing of LPA (Limited Partnership Agreement) and Subscription Agreement documents. The system replaces a manual review process costing ~$1M/year by using LLM-powered agents to classify, extract structured data, judge extraction confidence, summarize, and enable RAG-based retrieval across ingested documents. Single-user platform with no authentication or multi-tenancy.

---

## 2. Problem Statement

Fund operations and legal analysts at a PE firm spend approximately $1M/year manually reviewing LPA and Subscription Agreement documents. The current process involves:

- Manual reading and interpretation of dense legal documents
- Manual extraction of key financial terms (management fees, carried interest, fund terms, etc.)
- High error rates due to document volume and complexity
- No structured searchability across the document corpus
- No standardized extraction schemas — each analyst interprets differently

The platform automates this end-to-end: from document upload through parsing, classification, structured extraction with confidence scoring, summarization, and semantic retrieval.

---

## 3. Target Users

**Primary:** Fund operations / legal analysts at a PE firm

- **Technical level:** Semi-technical — comfortable with document management tools, browser-based applications, and structured workflows. Do not require hand-holding but are not developers.
- **Context of use:** Desktop workstations during business hours. Reviewing batches of PE legal documents, extracting key terms, and querying across the document corpus.
- **Key need:** Accurate extraction with transparent confidence scoring so they can focus review time on low-confidence fields rather than reading every document end-to-end.

---

## 4. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Documents processed per week | Measurable increase over manual baseline | Weekly throughput tracking |
| Extraction accuracy | High % of fields extracted correctly (high confidence) | Confidence distribution analysis |
| Manual review time reduction | Measurable % reduction | Time-to-review per document |
| Low-confidence field rate | Decreasing over time as schemas improve | % of fields flagged for review |
| Cost reduction | Significant reduction from $1M/year baseline | Annual operational cost comparison |

---

## 5. Scope

### In Scope (v1)

| Feature | Description |
|---------|-------------|
| Document upload | Single and bulk file upload with drag-drop, dedup via SHA-256 |
| Document parsing | Reducto Cloud API → markdown (PDF, DOCX, XLSX, images) |
| Content editing | TipTap rich text editor with split-view (original vs. parsed) |
| Classification | LLM-powered classification against user-defined categories |
| Extraction | Schema-driven structured field extraction with Pydantic models |
| Confidence judging | Separate Judge agent evaluates extraction quality per field |
| Extraction review | 3-column UI with confidence badges, hard gate on low-confidence fields |
| Summarization | LLM-generated document summaries |
| RAG ingestion | Semantic chunking → Weaviate with hybrid search (BM25 + vector) |
| RAG chat | Conversational retrieval with citations, scope filtering |
| Config management | CRUD for document categories and extraction field schemas |
| Bulk processing | Automated pipeline (parse → classify → extract → judge → summarize → ingest) with progress tracking |
| Document state machine | UPLOADED → PARSED → EDITED → CLASSIFIED → EXTRACTED → SUMMARIZED → INGESTED |

### Out of Scope (v1)

| Feature | Reason |
|---------|--------|
| Authentication / authorization | Single-user platform — no multi-tenancy |
| User management | Single-user |
| Organization management | Single-user |
| Cloud storage (S3/GCS) | Local filesystem only for v1 |
| Export / reporting | Not in initial requirements |
| Mobile / tablet support | Desktop-only for analysts at workstations |

---

## 6. MVP Definition

**Smallest deployable slice that delivers real value:**

Single-document end-to-end flow:
1. Upload a document (single file)
2. Parse via Reducto → markdown
3. Edit parsed content (TipTap split-view)
4. Classify against user-defined categories
5. Extract structured fields based on category schema
6. Judge confidence per extracted field
7. Review extraction results (hard gate on low-confidence fields)
8. Summarize document
9. Ingest into Weaviate (semantic chunks)
10. RAG chat — query the ingested document

**MVP excludes:** Bulk processing pipeline, bulk upload UI, bulk job dashboard. These are post-MVP features.

**MVP includes config management** (categories + extraction fields) as a prerequisite for classification and extraction.

---

## 7. Alternatives Considered

### Option A — DeepAgents Orchestrator (CHOSEN)

Full DeepAgent with subagents (classifier, extractor, judge, summarizer, RAG retriever). LangGraph StateGraph for bulk pipeline.

- **Advantages:** Built-in middleware (filesystem, summarization, PII filtering), subagent delegation, checkpointing, memory, extensibility
- **Disadvantages:** Framework dependency (DeepAgents v0.4.12), learning curve, abstraction overhead
- **Chosen because:** Consistency across all agent operations, built-in checkpointing/resumability, PII middleware support, and future extensibility as processing may evolve beyond single-turn operations

### Option B — Direct OpenAI Structured Output (REJECTED)

No agent framework. Each operation calls OpenAI directly with Pydantic response models.

- **Rejected because:** Loses agent middleware (especially PII filtering), no built-in memory/checkpointing, manual orchestration burden

### Option C — Hybrid Approach (REJECTED)

Direct OpenAI for single-turn operations, DeepAgents only for RAG retriever.

- **Rejected because:** Two patterns to maintain, inconsistent architecture, PII middleware would need separate implementation for non-agent operations

---

## 8. Technical Architecture

### Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + Vite + TypeScript + Tailwind CSS + TanStack Query + TipTap + Axios |
| Backend | Python 3.13 + FastAPI |
| Agent framework | DeepAgents 0.4.12 (built on LangGraph) |
| LLM | OpenAI GPT-5.4-mini |
| Document parser | Reducto Cloud API |
| Database | PostgreSQL 16 (Docker) |
| Vector store | Weaviate (Docker, hybrid search) |
| Embeddings | OpenAI (via Weaviate text2vec-openai module) |
| Chunking | LangChain SemanticChunker |

### System Architecture

```
React (Vite, port 5173) ──▶ FastAPI Backend (port 8000)
                                │
                                ├── DeepAgent Orchestrator (single-doc)
                                │   ├── Classifier Subagent
                                │   ├── Extractor Subagent
                                │   ├── Judge Subagent
                                │   ├── Summarizer Subagent
                                │   └── RAG Retriever Subagent
                                │
                                ├── LangGraph Bulk Pipeline (bulk)
                                │   parse → classify → extract → judge → summarize → ingest
                                │
                                ├── Reducto API (parsing)
                                ├── PostgreSQL (Docker, port 5432)
                                └── Weaviate (Docker, port 8080)
```

### Key Architecture Decisions

- **Local dev servers** for backend/frontend; Docker Compose for PostgreSQL + Weaviate only
- **Repository pattern** with SQLAlchemy 2.0 async + asyncpg
- **Alembic** for database migrations
- **Local filesystem** for document storage (configurable paths via config.yml)
- **Bulk concurrency:** 10 concurrent documents per run
- **PII filtering via DeepAgents middleware** (pre-model callback) — redacts investor names, SSN/tax IDs, addresses, bank details, phone numbers before LLM calls; fund names and financial terms pass through unredacted

---

## 9. Data Model Overview

### Core Tables

| Table | Purpose |
|-------|---------|
| `documents` | Document metadata, status state machine, file hash for dedup |
| `document_categories` | User-defined categories with classification criteria |
| `extraction_schemas` | Versioned extraction field definitions per category (YAML) |
| `extraction_fields` | Individual field definitions (name, type, description, examples) |
| `extracted_values` | Extracted data with confidence, source text, review status |
| `document_summaries` | Generated summaries with content hash for cache invalidation |
| `bulk_jobs` | Bulk processing job tracking |
| `bulk_job_documents` | Per-document status within bulk jobs |

### Document State Machine

```
UPLOADED → PARSED → CLASSIFIED → EXTRACTED → SUMMARIZED → INGESTED
                ↘
             EDITED → (re-enters flow at CLASSIFIED)
```

### Weaviate Collection

```
DocumentChunks: content, document_id, document_name, document_category,
                file_name, chunk_index, created_at
Vectorizer: text2vec-openai | Search: hybrid (BM25 + vector)
```

---

## 10. External Integrations

| Integration | Purpose | Notes |
|-------------|---------|-------|
| Reducto Cloud API | Document parsing (PDF, DOCX, XLSX, images → markdown) | API key required, cloud service |
| OpenAI API | LLM (GPT-5.4-mini) for classification, extraction, judging, summarization, RAG | API key required |
| OpenAI Embeddings | Vector embeddings via Weaviate text2vec-openai module | Same API key |
| PostgreSQL 16 | Structured data storage | Local Docker container |
| Weaviate | Vector store with hybrid search | Local Docker container |

---

## 11. Edge Cases & Constraints

### Failure Handling

| Scenario | Behavior |
|----------|----------|
| Reducto parsing fails (corrupted file, unsupported format, timeout) | Document stays in UPLOADED state; error reason shown in UI; user can retry |
| LLM call fails (rate limit, timeout, malformed response) | Automatic retry up to 3 times with backoff; then mark as failed and surface to user |
| Extraction produces low-confidence fields | Hard gate — user MUST review all low-confidence fields before proceeding to summarize/ingest |
| Duplicate file upload | SHA-256 dedup — skip re-parsing if hash unchanged; overwrite file if re-uploaded |
| Bulk pipeline per-document failure | Failures don't block other documents; failed docs logged with error message |

### PII & Sensitive Data

- PE documents contain investor names, SSN/tax IDs, addresses, bank account details, phone numbers
- **DeepAgents PII middleware** (pre-model callback) redacts PII before LLM calls
- **Redacted:** Investor names, SSN/tax IDs, addresses, bank account details, phone numbers
- **Not redacted:** Fund names, financial terms (management fees, carried interest, preferred return, fund term) — these are extraction targets
- Original unredacted content stored locally only — never sent to LLM
- Local filesystem storage — no cloud storage in v1

### Operational Constraints

- No uptime SLA (internal tool / R&D)
- Reducto and OpenAI API rate limits apply
- Bulk mode: 10 concurrent documents per run
- No budget constraints specified for API usage

---

## 12. UI Context

### Pages / Routes

| Route | Purpose |
|-------|---------|
| `/` | Dashboard — document list, status overview |
| `/upload` | Upload — single + bulk mode with drag-drop |
| `/documents/:id/parse` | Parse results + TipTap editor (split view) |
| `/documents/:id/classify` | Classification result + override |
| `/documents/:id/extract` | 3-column extraction results view |
| `/documents/:id/summary` | Generated summary with regenerate |
| `/documents/:id/chat` | RAG chat interface |
| `/config/categories` | Manage document categories + classification criteria |
| `/config/extraction-fields` | Manage extraction fields per category |
| `/bulk` | Bulk job dashboard (progress, status) |

### Design Direction

- **Desktop-only** — analysts at workstations
- **Functional accessibility** — keyboard navigation, readable contrast (no formal WCAG level)
- **Consumer-facing design bar** — high polish expected (calibration threshold: 8/10)

### Reference Apps (Pattern Reuse)

**Frontend reference:** `document_intelligence_fe_v2` (Next.js 16 / React 19 / Tailwind / TanStack Query)
- Reuse: Upload with drag-drop & dedup, TipTap split-view editor, RAG chat with citations, bulk progress polling, extraction workflow, multi-view document list, design token system (color palettes, shadows, animations)
- Adapt: Strip multi-tenancy/auth, convert Next.js App Router → Vite/React Router

**Backend reference:** `doc_intelligence_ai_v3.0` (FastAPI / SQLAlchemy 2.0 async / LangGraph)
- Reuse: Agent factory singleton, composable middleware stack (PII detector, retry, rate limiter), LangGraph StateGraph pipeline, repository pattern, bulk job tracking, async utilities
- Adapt: Replace Gemini → OpenAI, LlamaParse → Reducto, GCS → local filesystem, pgvector → Weaviate, strip multi-tenancy

---

## 13. Open Questions

| # | Question | Impact |
|---|----------|--------|
| 1 | What specific PII regex patterns should the DeepAgents middleware use? Should we port the patterns from the reference backend's PIIDetector? | PII middleware implementation |
| 2 | Should extraction schemas be seeded with default LPA fields on first run, or must users always configure from scratch? | Onboarding experience |
| 3 | What is the target number of documents in the corpus at steady state? (Affects Weaviate sizing and chunking strategy) | Infrastructure sizing |
| 4 | Should RAG chat support multi-turn conversation with memory, or is single-turn Q&A sufficient for MVP? | Agent complexity |
| 5 | Are there specific document formatting patterns in PE LPAs that Reducto may struggle with (e.g., watermarks, scanned annexes)? | Parser fallback strategy |
