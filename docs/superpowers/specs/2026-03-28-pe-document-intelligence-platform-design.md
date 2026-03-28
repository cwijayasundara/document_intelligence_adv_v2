# PE Document Intelligence Platform — Design Spec

## 1. Overview

A document intelligence platform for a private equity (PE) client that processes LPA and Subscription Agreement documents through a multi-step workflow: upload, parse, edit, classify, extract, summarize, ingest, and retrieve.

**Two processing modes:**
- **Single document:** User-driven, step-by-step with editing and review
- **Bulk:** Automated pipeline with multi-threading (no edit step)

**No multi-tenancy.** Single-user platform — no auth, org, or user management.

---

## 2. Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + Vite + TypeScript + Tailwind CSS + TanStack Query |
| Backend | Python 3.13 + FastAPI |
| Agent framework | DeepAgents (built on LangGraph) |
| LLM | OpenAI GPT-5.4-mini |
| Document parser | Reducto Cloud API |
| Database | PostgreSQL 16 (Docker) |
| Vector store | Weaviate (Docker, hybrid search) |
| Embeddings | OpenAI (via Weaviate text2vec-openai module) |
| Chunking | LangChain SemanticChunker |
| Rich text editor | TipTap |
| HTTP client | Axios |

---

## 3. System Architecture

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

- Single backend API (one base URL)
- All folder paths configured via `config.yml`, secrets via `.env`
- Docker Compose for PostgreSQL + Weaviate

---

## 4. Document Processing State Machine

**States (stored in PostgreSQL `documents.status`):**

```
UPLOADED → PARSED → CLASSIFIED → EXTRACTED → SUMMARIZED → INGESTED
                ↘
             EDITED → (re-enters flow at CLASSIFIED)
```

- Each transition validated (can't extract before classifying)
- Single-doc: user triggers each transition via UI
- Bulk: automatic flow through all states
- File dedup via SHA-256 hash — skip re-parsing if hash unchanged

---

## 5. Database Schema

### documents
| Column | Type | Description |
|--------|------|-------------|
| id | UUID, PK | |
| file_name | VARCHAR | Original filename |
| original_path | VARCHAR | Path in /upload |
| parsed_path | VARCHAR | Path in /parsed (markdown) |
| file_hash | VARCHAR | SHA-256 for dedup/versioning |
| status | ENUM | uploaded, parsed, edited, classified, extracted, summarized, ingested |
| document_category_id | FK → document_categories | |
| file_type | VARCHAR | pdf, docx, xlsx, png, etc. |
| file_size | BIGINT | |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### document_categories
| Column | Type | Description |
|--------|------|-------------|
| id | UUID, PK | |
| name | VARCHAR | e.g., "LPA", "Subscription Agreement" |
| description | TEXT | |
| classification_criteria | TEXT | Prompt/rules for classifier LLM |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### extraction_schemas
| Column | Type | Description |
|--------|------|-------------|
| id | UUID, PK | |
| category_id | FK → document_categories | |
| version | INT | |
| schema_yaml | TEXT | YAML defining fields to extract |
| created_at | TIMESTAMP | |

### extraction_fields
| Column | Type | Description |
|--------|------|-------------|
| id | UUID, PK | |
| schema_id | FK → extraction_schemas | |
| field_name | VARCHAR | e.g., "fund_name" |
| display_name | VARCHAR | e.g., "Fund Name" |
| description | TEXT | For LLM context |
| examples | TEXT | Example values for LLM |
| data_type | VARCHAR | string, number, date, currency, percentage |
| required | BOOL | |
| sort_order | INT | |

### extracted_values
| Column | Type | Description |
|--------|------|-------------|
| id | UUID, PK | |
| document_id | FK → documents | |
| field_id | FK → extraction_fields | |
| extracted_value | TEXT | |
| source_text | TEXT | Original passage the value came from |
| confidence | ENUM | high, medium, low |
| confidence_reasoning | TEXT | Judge's explanation |
| requires_review | BOOL | True if confidence is low |
| reviewed | BOOL | User has confirmed/edited |
| created_at | TIMESTAMP | |

### document_summaries
| Column | Type | Description |
|--------|------|-------------|
| id | UUID, PK | |
| document_id | FK → documents | |
| summary_text | TEXT | |
| content_hash | VARCHAR | SHA-256 for cache invalidation |
| created_at | TIMESTAMP | |

### bulk_jobs
| Column | Type | Description |
|--------|------|-------------|
| id | UUID, PK | |
| status | ENUM | pending, processing, completed, failed, partial_failure |
| total_documents | INT | |
| processed_count | INT | |
| failed_count | INT | |
| created_at | TIMESTAMP | |
| completed_at | TIMESTAMP | |

### bulk_job_documents
| Column | Type | Description |
|--------|------|-------------|
| id | UUID, PK | |
| job_id | FK → bulk_jobs | |
| document_id | FK → documents | |
| status | ENUM | pending, processing, completed, failed |
| error_message | TEXT | |
| processing_time_ms | INT | |

---

## 6. Agent Architecture

### Single-Document Flow — DeepAgent with Subagents

```python
orchestrator = create_deep_agent(
    model="openai:gpt-5.4-mini",
    tools=[parse_document, save_document, get_document_status],
    subagents=[classifier, extractor, judge, summarizer, rag_retriever],
    system_prompt="...",
    middleware=[FilesystemMiddleware, SubAgentMiddleware, SummarizationMiddleware],
    backend=FilesystemBackend(root="/data")
)
```

### Subagent Definitions

| Subagent | Purpose | Tools | Structured Output |
|----------|---------|-------|-------------------|
| Classifier | Categorize document against user-defined categories | `get_categories`, `get_parsed_content` | `ClassificationResult(category, reasoning)` |
| Extractor | Extract fields based on schema | `get_extraction_schema`, `get_parsed_content` | `ExtractionResult(fields: list[ExtractedField])` — each field has `value`, `source_text` |
| Judge | Evaluate extraction confidence | `get_extracted_values`, `get_parsed_content` | `JudgeResult(evaluations: list[FieldEvaluation])` — each has `confidence`, `reasoning` |
| Summarizer | Generate document summary | `get_parsed_content` | `SummaryResult(summary, key_topics)` |
| RAG Retriever | Query ingested documents | `weaviate_hybrid_search` | Free-form response with citations |

### Extraction + Judge Flow

1. User triggers extraction on a classified document
2. **Extractor subagent:**
   - Loads extraction schema (YAML) for the document's category
   - Reads parsed markdown content
   - Uses function calling with Pydantic schema to extract each field
   - Returns: field_name, extracted_value, source_text (the passage it found)
3. **Judge subagent** (separate LLM call for objectivity):
   - Receives: extracted values + source texts + original document
   - For each field evaluates:
     - Does the source_text actually support the extracted_value?
     - Is the source_text from a definitive section or ambiguous context?
     - Are there contradictions elsewhere in the document?
   - Returns: confidence (high/medium/low) + reasoning per field
4. Results saved to `extracted_values` table
5. Fields with low confidence get `requires_review=true`

### Confidence Scoring Criteria

| Level | Criteria |
|-------|----------|
| High | Source text explicitly states the value; no ambiguity; value matches expected format |
| Medium | Source text implies the value but requires interpretation; or multiple possible values found |
| Low | Source text is vague/indirect; value inferred from context; contradictory information exists; or no clear source passage found |

### Bulk Flow — LangGraph StateGraph

```
parse_node → classify_node → extract_node → judge_node → summarize_node → ingest_node → finalize_node
```

- Each node calls the same subagent functions used in single-doc flow
- `DocumentState` TypedDict carries document through the pipeline
- Concurrent processing: configurable (default 3 documents)
- Checkpointing via MemorySaver for resumability
- Per-document error handling — failures don't block other documents
- No edit step in bulk mode

---

## 7. Document Parsing

- **Parser:** Reducto Cloud API
- **Supported formats:** PDF, images (PNG, JPG, TIFF), Word (.docx), Excel (.xlsx)
- **Output:** Markdown with tables, structure preserved
- **Storage:** Parsed markdown saved to `/parsed/{filename}.md`
- **Dedup:** SHA-256 hash on upload. If `/parsed/{filename}.md` exists and hash matches → skip parsing. If hash differs → re-parse and overwrite.
- **Re-upload:** If file already exists in `/upload` → overwrite it

---

## 8. Document Classification

- User-defined categories stored in `document_categories` table
- Each category has a `classification_criteria` text field — free-form prompt guidance for the LLM
- Classifier subagent receives parsed content + all categories with criteria → returns best match + reasoning
- Default "Other/Unclassified" category for non-matching documents
- Categories managed via Config UI — can add/edit/remove anytime
- Result saved to `documents.document_category_id`

---

## 9. Extraction Schema Management

### Schema Lifecycle

```
User defines fields per category (UI) → saved to DB + YAML → used by Extractor subagent
```

### Field Definition (per category)

Each field has:
- `field_name` — machine name (e.g., `fund_name`)
- `display_name` — human label (e.g., "Fund Name")
- `description` — context for the LLM
- `examples` — example values for the LLM
- `data_type` — string, number, date, currency, percentage
- `required` — whether field must be extracted
- `sort_order` — display ordering

### Default LPA Fields

fund_name, general_partner, management_fee_rate, carried_interest_rate, preferred_return, fund_term, commitment_period, governing_law

### Generated YAML Schema

```yaml
category: LPA
version: 1
fields:
  - name: fund_name
    display_name: Fund Name
    description: The official name of the fund
    examples: ["Horizon Equity Partners IV", "Apex Growth Fund III"]
    data_type: string
    required: true
  # ... etc
```

### Dynamic Pydantic Model

Extractor builds a Pydantic model dynamically from the YAML/DB fields and passes it to DeepAgent via `response_format` for structured output.

---

## 10. Extraction Results Display

3-column layout:

| Field (+ confidence badge) | Extracted Value | Source Text |
|---------------------------|-----------------|-------------|
| Fund Name 🟢 High | Horizon Equity Partners IV | "...hereby establishes Horizon Equity Partners IV, a Delaware..." |
| Preferred Return 🟡 Medium | 8% | "...distributions shall first be made to partners until they have received an 8% cumulative..." |
| Fund Term 🔴 Low ⚠️ Requires Review [Edit] | 10 years | "...initial term...not to exceed ten years...subject to two one-year extensions..." |

- Low confidence rows highlighted, marked "Requires Review"
- User can click "Edit" to correct the value inline
- Must review all low-confidence fields before saving
- "Save" persists to `extracted_values` table with `reviewed=true`

---

## 11. RAG — Ingestion & Retrieval

### Ingestion

- **Chunking:** LangChain `SemanticChunker` — splits on semantic boundaries
- **Fallback:** 512 tokens max, 100 token overlap (configurable in `config.yml`)
- **Metadata per chunk:** document_id, document_name, document_category, file_name, chunk_index, created_at

### Weaviate Collection

```
Collection: DocumentChunks
├── content (text)
├── document_id (text)
├── document_name (text)
├── document_category (text)
├── file_name (text)
├── chunk_index (int)
├── created_at (date)
├── Vectorizer: text2vec-openai
└── Search: hybrid (BM25 + vector)
```

### Hybrid Search

- Weaviate native hybrid: BM25 keyword + vector semantic
- `alpha` parameter: 0 = pure keyword, 1 = pure semantic, 0.5 = balanced (default)
- User selects mode in UI: Semantic, Keyword, Hybrid

### Retrieval — RAG Subagent

1. User selects scope: single document, all documents, or by category
2. User enters query
3. RAG subagent calls `weaviate_hybrid_search` with query + filters + alpha
4. Gets top-K chunks (default 5, configurable)
5. Constructs answer with citations (chunk text, document name, relevance score)

### Re-ingestion

- When parsed document is edited, old chunks deleted from Weaviate and re-ingested
- Triggered automatically on save from edit screen

---

## 12. Frontend Architecture

### Tech Stack
React 19 + Vite + TypeScript + Tailwind CSS + TanStack Query + TipTap + Axios

### Pages

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

### Components Reused from Reference App

| Component | Adaptation |
|-----------|------------|
| `DocumentUploadSection` | Remove folder/org selection, simplify |
| `RichTextEditor` + `ParseResultsPage` | Reuse split-view pattern directly |
| `ChatPage` | Replace Gemini search with Weaviate hybrid, add scope filters |
| `useBulkUpload` | Reuse polling pattern, adapt status enums |
| `ExtractionPage` | Replace 4-step wizard with 3-column view + confidence badges |

### New Components

| Component | Purpose |
|-----------|---------|
| `CategoryManager` | CRUD for document categories with criteria text editor |
| `ExtractionFieldEditor` | Add/edit/reorder fields per category with examples |
| `ExtractionResultsTable` | 3-column layout: field, value+confidence, source text |
| `ConfidenceReviewPanel` | Low-confidence field review gate before saving |
| `ClassificationResult` | Show detected category with reasoning, allow override |
| `DocumentStatusBadge` | Visual state machine indicator per document |
| `BulkJobDashboard` | Job list with per-document progress tracking |

### State Management
- TanStack Query for all server state
- React Context for UI state only (theme, active filters)
- Axios with single base URL, snake_case ↔ camelCase transformers

---

## 13. Project Structure

```
document_intelligence_adv_v2/
├── backend/
│   ├── src/
│   │   ├── agents/
│   │   │   ├── orchestrator.py
│   │   │   ├── classifier.py
│   │   │   ├── extractor.py
│   │   │   ├── judge.py
│   │   │   ├── summarizer.py
│   │   │   └── rag_retriever.py
│   │   ├── api/
│   │   │   ├── app.py
│   │   │   ├── routers/
│   │   │   │   ├── documents.py
│   │   │   │   ├── parse.py
│   │   │   │   ├── classify.py
│   │   │   │   ├── extract.py
│   │   │   │   ├── summarize.py
│   │   │   │   ├── ingest.py
│   │   │   │   ├── rag.py
│   │   │   │   ├── config.py
│   │   │   │   └── bulk.py
│   │   │   └── schemas/
│   │   ├── bulk/
│   │   │   ├── state_graph.py
│   │   │   ├── service.py
│   │   │   └── queue.py
│   │   ├── db/
│   │   │   ├── models.py
│   │   │   ├── connection.py
│   │   │   └── repositories/
│   │   ├── rag/
│   │   │   ├── chunker.py
│   │   │   ├── weaviate_client.py
│   │   │   └── embeddings.py
│   │   ├── parser/
│   │   │   └── reducto.py
│   │   ├── storage/
│   │   │   └── local.py
│   │   └── main.py
│   ├── config.yml
│   ├── schemas/
│   │   └── lpa.yml
│   ├── requirements.txt
│   ├── .env.example
│   └── alembic/
│       └── versions/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── documents/
│   │   │   ├── parse/
│   │   │   ├── classify/
│   │   │   ├── extract/
│   │   │   ├── summary/
│   │   │   ├── chat/
│   │   │   ├── config/
│   │   │   ├── bulk/
│   │   │   └── ui/
│   │   ├── hooks/
│   │   ├── lib/
│   │   │   ├── api/
│   │   │   └── config.ts
│   │   ├── types/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── tsconfig.json
├── docker-compose.yml
├── docs/
└── data/
    ├── upload/
    ├── parsed/
    └── schemas/
```

---

## 14. Configuration

### config.yml

```yaml
storage:
  upload_dir: "./data/upload"
  parsed_dir: "./data/parsed"
  schemas_dir: "./schemas"

chunking:
  max_tokens: 512
  overlap_tokens: 100

bulk:
  concurrent_documents: 3
  max_retries: 3
  retry_delay_seconds: 30

rag:
  default_search_mode: "hybrid"
  default_alpha: 0.5
  top_k: 5

extraction:
  default_schema_dir: "./schemas"
```

### .env.example

```
OPENAI_API_KEY=sk-...
REDUCTO_API_KEY=...
DATABASE_URL=postgresql+asyncpg://doc_intel:doc_intel_dev@localhost:5432/doc_intel
WEAVIATE_URL=http://localhost:8080
OPENAI_MODEL=gpt-5.4-mini
```

### docker-compose.yml

```yaml
services:
  postgres:
    image: postgres:16
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: doc_intel
      POSTGRES_USER: doc_intel
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-doc_intel_dev}
    volumes:
      - pgdata:/var/lib/postgresql/data

  weaviate:
    image: semitechnologies/weaviate:latest
    ports:
      - "8080:8080"
      - "50051:50051"
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      DEFAULT_VECTORIZER_MODULE: 'text2vec-openai'
      ENABLE_MODULES: 'text2vec-openai'
      OPENAI_APIKEY: ${OPENAI_API_KEY}

volumes:
  pgdata:
```

---

## 15. API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/documents/upload` | Upload single/multiple files |
| GET | `/api/v1/documents` | List all documents with status |
| GET | `/api/v1/documents/:id` | Get document details |
| DELETE | `/api/v1/documents/:id` | Delete document |
| POST | `/api/v1/parse/:id` | Parse document via Reducto |
| GET | `/api/v1/parse/:id/content` | Get parsed markdown content |
| PUT | `/api/v1/parse/:id/content` | Save edited content |
| POST | `/api/v1/classify/:id` | Classify document |
| POST | `/api/v1/extract/:id` | Extract fields from document |
| GET | `/api/v1/extract/:id/results` | Get extraction results |
| PUT | `/api/v1/extract/:id/results` | Update/review extracted values |
| POST | `/api/v1/summarize/:id` | Generate summary |
| GET | `/api/v1/summarize/:id` | Get summary |
| POST | `/api/v1/ingest/:id` | Ingest document into Weaviate |
| POST | `/api/v1/rag/query` | RAG query with filters |
| GET | `/api/v1/config/categories` | List categories |
| POST | `/api/v1/config/categories` | Create category |
| PUT | `/api/v1/config/categories/:id` | Update category |
| DELETE | `/api/v1/config/categories/:id` | Delete category |
| GET | `/api/v1/config/categories/:id/fields` | List extraction fields |
| POST | `/api/v1/config/categories/:id/fields` | Create/update fields |
| POST | `/api/v1/bulk/upload` | Start bulk processing job |
| GET | `/api/v1/bulk/jobs` | List bulk jobs |
| GET | `/api/v1/bulk/jobs/:id` | Get job status + per-document progress |
