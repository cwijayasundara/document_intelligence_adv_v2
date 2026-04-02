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
                                │   ├── Classifier Subagent (hybrid: filename + content/summary)
                                │   ├── Extractor Subagent (value + source text citation)
                                │   ├── Judge Subagent (field-aware confidence scoring)
                                │   ├── Summarizer Subagent (PE-attribute-preserving)
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
- API keys loaded from `.env` via `pydantic_settings` and exported to `os.environ` for SDK access

---

## 4. Document Processing State Machine

**States (stored in PostgreSQL `documents.status`):**

```
UPLOADED → PARSED → CLASSIFIED → EXTRACTED → SUMMARIZED → INGESTED
                ↘                     ↑           ↑
             EDITED ──────────────────┘           │
                                                  │
           (re-classify and re-extract allowed from any downstream state)
```

**Transition rules:**

| From | Allowed targets |
|------|----------------|
| uploaded | parsed |
| parsed | edited, classified, summarized |
| edited | classified, summarized |
| classified | classified, extracted, summarized |
| extracted | classified, extracted, summarized |
| summarized | classified, extracted, summarized, ingested |
| ingested | — |

- Each transition validated by state machine (`services/state_machine.py`)
- Re-classification and re-extraction allowed from any post-parse state
- Single-doc: user triggers each transition via dashboard action icons
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
| parse_confidence_pct | FLOAT | Parse confidence from Reducto (0-100) |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### document_categories
| Column | Type | Description |
|--------|------|-------------|
| id | UUID, PK | |
| name | VARCHAR | e.g., "Limited Partnership Agreement" |
| description | TEXT | Rich description of the document type |
| classification_criteria | TEXT | Detailed criteria mapping extraction fields to classification signals |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

**Default seeded categories:** Limited Partnership Agreement, Subscription Agreement, Side Letter, Other/Unclassified.

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

**Default seeded LPA fields:** fund_name, general_partner, management_fee_rate, carried_interest_rate, preferred_return, fund_term, commitment_period, governing_law.

### extracted_values
| Column | Type | Description |
|--------|------|-------------|
| id | UUID, PK | |
| document_id | FK → documents | |
| field_id | FK → extraction_fields | |
| extracted_value | TEXT | |
| source_text | TEXT | Verbatim quote from the document supporting this value |
| confidence | VARCHAR(10) | high, medium, low |
| confidence_reasoning | TEXT | Judge's explanation |
| requires_review | BOOL | True if low confidence, empty required field, or medium + empty |
| reviewed | BOOL | User has confirmed/edited |
| created_at | TIMESTAMP | |

### document_summaries
| Column | Type | Description |
|--------|------|-------------|
| id | UUID, PK | |
| document_id | FK → documents | |
| summary_text | TEXT | |
| key_topics | JSONB | Array of key topic strings |
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

| Subagent | Purpose | Input Signals | Structured Output |
|----------|---------|---------------|-------------------|
| Classifier | Categorize document | File name hints + summary (preferred) or full content + category criteria | `ClassificationResult(category_id, category_name, confidence, reasoning)` |
| Extractor | Extract fields with source citations | Full parsed content + field definitions with examples | Dynamic Pydantic model: `{field}_value` + `{field}_source` per field |
| Judge | Evaluate extraction confidence | Extracted values + source quotes + full content + field metadata (type, required, examples) | `JudgeResult(evaluations: list[FieldEvaluation])` |
| Summarizer | Generate PE-attribute-preserving summary | Full parsed content (no truncation) | `SummaryResult(summary, key_topics)` |
| RAG Retriever | Query ingested documents | `weaviate_hybrid_search` | Free-form response with citations |

### Classification — Hybrid Two-Signal Approach

```
File Name Heuristic (regex patterns)
         +
Content/Summary LLM Call (with file name + category criteria)
         ↓
ClassificationResult with confidence score (0-100)
```

1. **File name signal:** Regex patterns detect category hints (e.g., `LPA_*` → "Limited Partnership Agreement", `Sub_*` → "Subscription Agreement", `Side_Letter_*` → "Side Letter"). Included as a supporting signal in the prompt — content always takes priority.

2. **Content signal:** Prefers document summary when available (more focused, retains PE attributes). Falls back to full parsed content (no truncation). Includes PE-specific few-shot examples in the system prompt for each category type.

3. **Confidence scoring:**
   - 90-100: Strong match — multiple defining attributes present
   - 70-89: Good match — key attributes present but some missing
   - 50-69: Moderate match — some indicators, ambiguous
   - Below 50: Weak match — few indicators, likely a guess

4. **Fallback chain:** Structured response → text matching (confidence=50) → "Other/Unclassified" (confidence=20)

### Extraction + Judge Flow

1. User triggers extraction on a classified document
2. **Extractor subagent:**
   - Loads extraction schema for the document's category from DB
   - Builds a dynamic Pydantic model with **two fields per extraction field**: `{name}` (value) and `{name}_source` (verbatim quote)
   - System prompt instructs: quote exact passages, include surrounding context, preserve original formatting
   - Field examples included in prompt for better accuracy
   - Returns: field_name, extracted_value, source_text per field
3. **Judge subagent** (separate LLM call for objectivity):
   - Receives: extracted values + source quotes + full document + **field metadata** (data_type, required, examples)
   - Per-field evaluation prompt shows expected type, required status, and example values
   - For each field evaluates:
     - **Source match:** Does the value appear in the cited source quote?
     - **Format validity:** Does the value match the expected data type?
     - **Completeness:** Is the full value captured?
     - **Source quality:** Is the quote verbatim from the document?
   - Returns: confidence (high/medium/low) + reasoning per field
4. Results saved to `extracted_values` table AND `data/extraction/{doc_id}.json`
5. **Review flagging logic:**
   - LOW confidence → requires review
   - MEDIUM confidence + empty value → requires review
   - Required field + empty value → requires review
6. **Heuristic fallback** (when LLM structured response fails):
   - Empty value → LOW
   - Value present but no source quote → MEDIUM
   - Value appears in source quote → HIGH

### Confidence Scoring Criteria

| Level | Criteria |
|-------|----------|
| High | Source quote explicitly states the value; correct format; complete extraction |
| Medium | Source implies the value but not verbatim; or format slightly off; or no source quote provided |
| Low | No value extracted; no supporting source; wrong format; or source appears fabricated |

### Summarizer — PE-Attribute Preservation

The summarizer's system prompt explicitly instructs the LLM to preserve 17 key PE attributes in the summary:
- Fund Name, General Partner, Limited Partners
- Management Fee Rate, Carried Interest Rate, Preferred Return / Hurdle Rate
- Fund Term, Commitment Period / Investment Period
- Distribution Waterfall, Governing Law, Capital Commitment amounts
- Key Person provisions, Clawback provisions
- Investor representations, Fee discounts, MFN clauses, Co-investment rights

Full parsed content is sent (no truncation) to ensure no attributes are lost.

### Bulk Flow — LangGraph StateGraph

```
parse_node → classify_node → extract_node → judge_node → summarize_node → ingest_node → finalize_node
```

- Each node calls the same subagent functions used in single-doc flow
- Classify node passes file_name and optional summary to the hybrid classifier
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
- Each category has rich `description` and `classification_criteria` fields
- **Hybrid classifier** uses two signals:
  1. File name regex patterns (LPA, Subscription, Side Letter hints)
  2. LLM classification using summary (preferred) or full content
- File name is a supporting signal only — content takes priority
- Confidence score (0-100) returned with every classification
- PE-specific few-shot examples in system prompt for each category type
- Default seeded categories: LPA (with 8 extraction fields), Subscription Agreement, Side Letter, Other/Unclassified
- Categories managed via inline edit UI (no modals)
- Result saved to `documents.document_category_id`
- Re-classification allowed from any downstream state

---

## 9. Extraction Schema Management

### Schema Lifecycle

```
User defines fields per category (inline editable table) → saved to DB → used by Extractor subagent
```

### Field Definition (per category)

Each field has:
- `field_name` — machine name, auto-generated from display name (e.g., `fund_name`)
- `display_name` — human label (e.g., "Fund Name")
- `description` — context for the LLM
- `examples` — example values for the LLM (included in extraction prompt)
- `data_type` — string, number, date, currency, percentage
- `required` — whether field must be extracted (affects review flagging)
- `sort_order` — display ordering

Fields are **per document category, not per user** — shared across all documents of that type.

### Default LPA Fields (seeded at startup)

| # | Field | Type | Required |
|---|-------|------|----------|
| 1 | Fund Name | string | yes |
| 2 | General Partner | string | yes |
| 3 | Management Fee Rate | percentage | yes |
| 4 | Carried Interest Rate | percentage | yes |
| 5 | Preferred Return | percentage | yes |
| 6 | Fund Term | string | yes |
| 7 | Commitment Period | string | yes |
| 8 | Governing Law | string | no |

### Dynamic Pydantic Model

Extractor builds a Pydantic model dynamically from the DB fields. For each field, two properties are generated:
- `{field_name}` — the extracted value (typed per data_type)
- `{field_name}_source` — verbatim source quote from the document

This is passed to DeepAgent via `response_format` for structured output.

---

## 10. Extraction Results Display

Full-width table in the inline detail panel below the dashboard:

| Field | Extracted Value | Source Text | Confidence |
|-------|----------------|-------------|------------|
| Fund Name | Horizon Equity Partners IV, L.P. | "This Amended and Restated Limited Partnership Agreement of Horizon Equity Partners IV, L.P..." | high |
| Preferred Return | 8% | "distributions shall first be made to partners until they have received an 8% cumulative..." | high |
| Fund Term (Needs review) | 10 years | "...initial term...not to exceed ten years...subject to two one-year extensions..." | low |

- Source text shown in italics with quotation marks; long sources collapsible (click to expand)
- Low confidence rows show "Needs review" badge
- Confidence badges color-coded: green (high), amber (medium), red (low)
- Review flagging: LOW confidence, MEDIUM + empty, or required + empty

---

## 11. Caching Strategy

### Dual Storage (DB + Disk)

Both summaries and extraction results use the same caching pattern:

```
data/
  upload/          # original uploaded files
  parsed/          # parsed markdown ({filename}.md)
  summary/         # summary cache ({doc_id}.json)
  extraction/      # extraction cache ({doc_id}.json)
```

### Cache Format

```json
{
  "document_id": "uuid",
  "content_hash": "sha256 of parsed content",
  "results": [...]
}
```

### Cache Invalidation

- **Content-hash based:** SHA-256 of the parsed markdown content
- On extraction/summarization request: compute hash of current parsed content
- If disk cache exists AND `content_hash` matches → **cache hit**, skip LLM calls, return cached results
- If hash differs (document was re-parsed/edited) → **cache miss**, re-run LLM pipeline
- `force=true` query parameter bypasses cache for explicit re-extraction

### Flow

```
POST /extract/{doc_id}?force=false
  ↓
Compute SHA-256 of parsed content
  ↓
Check data/extraction/{doc_id}.json
  ↓
Cache hit? ──yes──▶ Return cached results, save to DB
  │
  no
  ↓
Run Extractor LLM → Run Judge LLM → Save to disk + DB → Return results
```

DB always receives the latest results (old values deleted before insert) to ensure API consistency. Disk cache avoids redundant LLM calls when content hasn't changed.

---

## 12. RAG — Ingestion & Retrieval

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

## 13. Frontend Architecture

### Tech Stack
React 19 + Vite + TypeScript + Tailwind CSS + TanStack Query + TipTap + Axios

### Pages

| Route | Purpose |
|-------|---------|
| `/` | Dashboard — card grid (default) or table view, inline detail panel |
| `/upload` | Upload — single + bulk mode with drag-drop |
| `/documents/:id/parse` | Parse results + TipTap editor (split view) |
| `/config/categories` | Manage document categories with inline edit form |
| `/config/extraction-fields` | Manage extraction fields per category (inline editable table) |
| `/bulk` | Bulk job dashboard (progress, status) |

### Dashboard Layout

```
┌──────────────────────────────────────────────────────┐
│ Dashboard                    [table|cards] [Upload]   │
├──────────────────────────────────────────────────────┤
│                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ Doc Card    │  │ Doc Card    │  │ Doc Card    │  │
│  │ Status badge│  │ Category    │  │ Confidence  │  │
│  │ ◇ ≡ ⇅ ↻  →│  │ ◇ ≡ ⇅ ↻  →│  │ ◇ ≡ ⇅ ↻  →│  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
│                                                       │
│  ┌─────────────────────────────────────────────────┐  │
│  │ Inline Detail Panel (when document selected)     │  │
│  │ ┌──────────────────────────────────────────────┐ │  │
│  │ │ Extracted Fields (full width table)           │ │  │
│  │ │ Field | Value | Source Text | Confidence      │ │  │
│  │ └──────────────────────────────────────────────┘ │  │
│  │ ┌──────────────────┬───────────────────────────┐ │  │
│  │ │ Summary          │ Parsed Content (scroll)   │ │  │
│  │ │ Key topics       │                           │ │  │
│  │ └──────────────────┴───────────────────────────┘ │  │
│  └─────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

### Action Icons (card & table views)

| Icon | Action | Condition |
|------|--------|-----------|
| ◇ Tag | Classify | Document has been parsed |
| ⇅ Extract | Extract fields | Document has been classified (has category) |
| ≡ Summarize | Generate summary | Document has been parsed, not yet summarized |
| ↻ Re-parse | Force re-parse | Document has been parsed |
| → Continue | Navigate to next step | Always |
| ✓ Check | Summarized indicator | Status is summarized/ingested |

- All actions show a spinner icon while loading
- Classify, Extract, and Summarize auto-open the inline detail panel on success

### Sidebar Navigation

```
Dashboard
Upload
Bulk Processing
──────────────
ADMIN
  Categories
  Extraction Fields
```

### Components

| Component | Purpose |
|-----------|---------|
| `DocumentCardGrid` | Card grid view (default) with action icons |
| `DocumentList` + `DocumentRow` | Table view with action icons |
| `DocumentDetailPanel` | Inline panel: extraction table + summary + parsed content |
| `CategoryManager` + `CategoryForm` | Inline CRUD for categories (no modals) |
| `ExtractionFieldEditor` | Inline editable table for extraction fields |
| `DocumentStatusBadge` | Color-coded status badge |
| `ConfidenceBadge` | Color-coded confidence level badge |

### State Management
- TanStack Query for all server state
- React Context for UI state only (theme, active filters)
- Axios with single base URL, snake_case ↔ camelCase transformers

---

## 14. Project Structure

```
document_intelligence_adv_v2/
├── backend/
│   ├── src/
│   │   ├── agents/
│   │   │   ├── orchestrator.py
│   │   │   ├── classifier.py        # Hybrid classifier (filename + content/summary)
│   │   │   ├── extractor.py         # Dynamic model with value + source pairs
│   │   │   ├── judge.py             # Field-aware confidence scoring
│   │   │   ├── summarizer.py        # PE-attribute-preserving summaries
│   │   │   ├── rag_retriever.py
│   │   │   ├── schemas/
│   │   │   │   ├── classification.py # ClassificationResult with confidence
│   │   │   │   ├── extraction.py     # ExtractedField, JudgeResult
│   │   │   │   └── summary.py
│   │   │   └── middleware/
│   │   │       └── pii_filter.py     # PII redaction with financial term passthrough
│   │   ├── api/
│   │   │   ├── app.py               # App factory + category/field seeding
│   │   │   ├── routers/
│   │   │   │   ├── documents.py      # Upload, list (with category name), get, delete
│   │   │   │   ├── parse.py
│   │   │   │   ├── classify.py       # Hybrid classification with summary preference
│   │   │   │   ├── extract.py        # Extraction with disk caching + force param
│   │   │   │   ├── summarize.py
│   │   │   │   ├── ingest.py
│   │   │   │   ├── rag.py
│   │   │   │   ├── config.py
│   │   │   │   ├── bulk.py
│   │   │   │   └── stream.py
│   │   │   └── schemas/
│   │   ├── bulk/
│   │   │   ├── nodes.py              # LangGraph nodes (updated classifier signature)
│   │   │   ├── state_graph.py
│   │   │   └── service.py
│   │   ├── db/
│   │   │   ├── models/
│   │   │   │   ├── documents.py      # Document + DocumentCategory + DocumentSummary
│   │   │   │   └── extraction.py     # ExtractionSchema + ExtractionField + ExtractedValue
│   │   │   ├── repositories/
│   │   │   │   ├── documents.py      # selectinload(category) for list queries
│   │   │   │   ├── categories.py
│   │   │   │   ├── extraction.py
│   │   │   │   └── extracted_values.py # Delete-before-insert for re-extraction
│   │   │   └── connection.py
│   │   ├── services/
│   │   │   ├── extraction_service.py # Disk caching with content-hash invalidation
│   │   │   ├── summarize_service.py  # Disk caching (same pattern)
│   │   │   ├── parse_service.py
│   │   │   └── state_machine.py      # Flexible re-classification/re-extraction
│   │   ├── config/
│   │   │   └── settings.py           # Includes extraction_dir
│   │   ├── parser/
│   │   │   └── reducto.py
│   │   ├── storage/
│   │   │   └── local.py
│   │   └── main.py                   # Exports OPENAI_API_KEY to os.environ
│   ├── config.yml
│   ├── .env
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── documents/
│   │   │   │   ├── DocumentCardGrid.tsx    # Card view with action icons
│   │   │   │   ├── DocumentDetailPanel.tsx # Inline extraction + summary panel
│   │   │   │   ├── DocumentList.tsx        # Table view
│   │   │   │   ├── DocumentRow.tsx         # Table row with action icons
│   │   │   │   └── DocumentStatusBadge.tsx
│   │   │   ├── config/
│   │   │   │   ├── CategoryManager.tsx     # Inline card list + form
│   │   │   │   ├── CategoryForm.tsx        # Inline edit form (no modal)
│   │   │   │   └── ExtractionFieldEditor.tsx # Inline editable table
│   │   │   ├── parse/
│   │   │   ├── ui/
│   │   │   │   └── Sidebar.tsx             # Main + Admin sections
│   │   │   └── ...
│   │   ├── hooks/
│   │   │   ├── useClassify.ts
│   │   │   ├── useExtraction.ts
│   │   │   ├── useExtractionFields.ts
│   │   │   ├── useSummary.ts
│   │   │   └── ...
│   │   ├── types/
│   │   │   ├── classify.ts         # ClassifyResponse with confidence
│   │   │   ├── extraction.ts       # ExtractionResult with sourceText
│   │   │   └── document.ts         # DocumentListItem with categoryName
│   │   ├── lib/api/
│   │   └── pages/
│   │       ├── DashboardPage.tsx   # Card view default, inline detail panel
│   │       ├── CategoriesPage.tsx
│   │       └── ExtractionFieldsPage.tsx
│   └── package.json
├── docker-compose.yml
├── data/
│   ├── upload/
│   ├── parsed/
│   ├── summary/        # {doc_id}.json with content_hash
│   └── extraction/     # {doc_id}.json with content_hash
└── docs/
```

---

## 15. Configuration

### config.yml

```yaml
storage:
  upload_dir: "./data/upload"
  parsed_dir: "./data/parsed"
  summary_dir: "./data/summary"
  extraction_dir: "./data/extraction"
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
```

### .env.example

```
OPENAI_API_KEY=sk-...
REDUCTO_API_KEY=...
REDUCTO_BASE_URL=https://platform.reducto.ai
DATABASE_URL=<async PostgreSQL connection string>
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

## 16. API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/documents/upload` | Upload single/multiple files |
| GET | `/api/v1/documents` | List all documents with status + category name |
| GET | `/api/v1/documents/:id` | Get document details |
| DELETE | `/api/v1/documents/:id` | Delete document |
| POST | `/api/v1/parse/:id` | Parse document via Reducto |
| GET | `/api/v1/parse/:id/content` | Get parsed markdown content |
| PUT | `/api/v1/parse/:id/content` | Save edited content |
| POST | `/api/v1/classify/:id` | Classify document (hybrid: filename + content/summary) |
| POST | `/api/v1/extract/:id?force=false` | Extract fields (cached unless force=true) |
| GET | `/api/v1/extract/:id/results` | Get extraction results with source text |
| PUT | `/api/v1/extract/:id/results` | Update/review extracted values |
| POST | `/api/v1/summarize/:id` | Generate summary (PE-attribute-preserving) |
| GET | `/api/v1/summarize/:id` | Get cached summary |
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
| GET | `/api/v1/health` | Health check |

---

## 17. Startup Seeding

On application startup (`app.py` lifespan handler), the following are seeded if the database is empty:

**Categories (4):**
1. **Limited Partnership Agreement** — Rich description + detailed classification criteria mapping all 8 extraction fields as classification signals
2. **Subscription Agreement** — Capital commitments, investor representations, AML certifications
3. **Side Letter** — Fee discounts, MFN clauses, co-investment rights
4. **Other/Unclassified** — Default fallback category

**LPA Extraction Fields (8):** Seeded when the LPA category exists but has no extraction schema. Creates schema version 1 with all 8 fields including descriptions and examples.
