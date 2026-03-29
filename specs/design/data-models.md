# Data Models — PE Document Intelligence Platform

**Version:** 1.0
**Date:** 2026-03-28

---

## Overview

10 tables across 3 domains:

- **Document Processing:** documents, document_categories, extraction_schemas, extraction_fields, extracted_values, document_summaries
- **Bulk Processing:** bulk_jobs, bulk_job_documents
- **Memory:** conversation_summaries, memory_entries

All tables use UUID v4 primary keys with server-side defaults. Timestamps use `TIMESTAMP WITH TIME ZONE`.

---

## 1. documents

Core document metadata and state machine status.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Primary key |
| file_name | VARCHAR(500) | NOT NULL | Original filename |
| original_path | VARCHAR(1000) | NOT NULL | Path in data/upload/ |
| parsed_path | VARCHAR(1000) | NULLABLE | Path in data/parsed/ (null until parsed) |
| file_hash | VARCHAR(64) | NOT NULL, INDEX | SHA-256 hex digest for dedup |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'uploaded', INDEX | One of: uploaded, parsed, edited, classified, extracted, summarized, ingested |
| document_category_id | UUID | FK -> document_categories.id, NULLABLE, INDEX | Assigned after classification |
| file_type | VARCHAR(20) | NOT NULL | pdf, docx, xlsx, png, jpg, tiff |
| file_size | BIGINT | NOT NULL | File size in bytes |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Updated on every state transition |

**Indexes:**
- `ix_documents_file_hash` on `file_hash` (dedup lookup)
- `ix_documents_status` on `status` (dashboard filtering)
- `ix_documents_category_id` on `document_category_id` (category filtering)
- `ix_documents_created_at` on `created_at DESC` (default sort)

**Relationships:**
- `document_category_id` -> `document_categories.id` (many-to-one)

**Example Record:**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "file_name": "horizon-lpa-2026.pdf",
  "original_path": "data/upload/horizon-lpa-2026.pdf",
  "parsed_path": "data/parsed/a1b2c3d4-e5f6-7890-abcd-ef1234567890.md",
  "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "status": "classified",
  "document_category_id": "f0e1d2c3-b4a5-9687-fedc-ba0987654321",
  "file_type": "pdf",
  "file_size": 2048576,
  "created_at": "2026-03-28T10:00:00Z",
  "updated_at": "2026-03-28T10:30:00Z"
}
```

---

## 2. document_categories

User-defined document classification categories.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Primary key |
| name | VARCHAR(200) | NOT NULL, UNIQUE | Category name (e.g., "LPA") |
| description | TEXT | NULLABLE | Human-readable description |
| classification_criteria | TEXT | NULLABLE | Prompt/rules for classifier LLM |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:**
- `uq_document_categories_name` UNIQUE on `name`

**Relationships:**
- One-to-many -> `documents` (via documents.document_category_id)
- One-to-many -> `extraction_schemas` (via extraction_schemas.category_id)

**Example Record:**
```json
{
  "id": "f0e1d2c3-b4a5-9687-fedc-ba0987654321",
  "name": "LPA",
  "description": "Limited Partnership Agreements",
  "classification_criteria": "Documents that establish a limited partnership fund, defining terms between general and limited partners including management fees, carried interest, fund term, and investor commitments.",
  "created_at": "2026-03-28T09:00:00Z",
  "updated_at": "2026-03-28T09:00:00Z"
}
```

---

## 3. extraction_schemas

Versioned extraction field definitions per category.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Primary key |
| category_id | UUID | FK -> document_categories.id, NOT NULL, INDEX | Parent category |
| version | INTEGER | NOT NULL, DEFAULT 1 | Schema version number |
| schema_yaml | TEXT | NULLABLE | Generated YAML representation |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:**
- `ix_extraction_schemas_category_id` on `category_id`
- `uq_extraction_schemas_category_version` UNIQUE on `(category_id, version)`

**Relationships:**
- `category_id` -> `document_categories.id` (many-to-one)
- One-to-many -> `extraction_fields` (via extraction_fields.schema_id)

**Example Record:**
```json
{
  "id": "11111111-2222-3333-4444-555555555555",
  "category_id": "f0e1d2c3-b4a5-9687-fedc-ba0987654321",
  "version": 1,
  "schema_yaml": "category: LPA\nversion: 1\nfields:\n  - name: fund_name\n    display_name: Fund Name\n    ...",
  "created_at": "2026-03-28T09:05:00Z"
}
```

---

## 4. extraction_fields

Individual field definitions within an extraction schema.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Primary key |
| schema_id | UUID | FK -> extraction_schemas.id, NOT NULL, INDEX | Parent schema |
| field_name | VARCHAR(200) | NOT NULL | Machine name (e.g., "fund_name") |
| display_name | VARCHAR(200) | NOT NULL | Human label (e.g., "Fund Name") |
| description | TEXT | NULLABLE | Context for LLM prompt |
| examples | TEXT | NULLABLE | Example values for LLM |
| data_type | VARCHAR(20) | NOT NULL, DEFAULT 'string' | string, number, date, currency, percentage |
| required | BOOLEAN | NOT NULL, DEFAULT false | Whether field must be extracted |
| sort_order | INTEGER | NOT NULL, DEFAULT 0 | Display ordering |

**Indexes:**
- `ix_extraction_fields_schema_id` on `schema_id`
- `uq_extraction_fields_schema_field` UNIQUE on `(schema_id, field_name)`

**Relationships:**
- `schema_id` -> `extraction_schemas.id` (many-to-one)
- One-to-many -> `extracted_values` (via extracted_values.field_id)

**Example Record:**
```json
{
  "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
  "schema_id": "11111111-2222-3333-4444-555555555555",
  "field_name": "management_fee_rate",
  "display_name": "Management Fee Rate",
  "description": "Annual management fee as a percentage of committed capital during the commitment period",
  "examples": "2.0%, 1.5%, 1.75%",
  "data_type": "percentage",
  "required": true,
  "sort_order": 3
}
```

---

## 5. extracted_values

Extracted data per document per field, with confidence scoring.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Primary key |
| document_id | UUID | FK -> documents.id, NOT NULL, INDEX | Source document |
| field_id | UUID | FK -> extraction_fields.id, NOT NULL, INDEX | Field definition |
| extracted_value | TEXT | NULLABLE | The extracted value |
| source_text | TEXT | NULLABLE | Original passage the value came from |
| confidence | VARCHAR(10) | NOT NULL | high, medium, low |
| confidence_reasoning | TEXT | NULLABLE | Judge's explanation |
| requires_review | BOOLEAN | NOT NULL, DEFAULT false | True if confidence is low |
| reviewed | BOOLEAN | NOT NULL, DEFAULT false | User has confirmed/edited |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:**
- `ix_extracted_values_document_id` on `document_id`
- `ix_extracted_values_field_id` on `field_id`
- `uq_extracted_values_doc_field` UNIQUE on `(document_id, field_id)`

**Relationships:**
- `document_id` -> `documents.id` (many-to-one)
- `field_id` -> `extraction_fields.id` (many-to-one)

**Example Record:**
```json
{
  "id": "99999999-8888-7777-6666-555555555555",
  "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "field_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
  "extracted_value": "2.0%",
  "source_text": "The Management Fee shall be equal to 2.0% per annum of aggregate Commitments during the Commitment Period.",
  "confidence": "high",
  "confidence_reasoning": "Source text explicitly states the management fee rate in a definitional clause. No ambiguity or contradictory provisions found.",
  "requires_review": false,
  "reviewed": false,
  "created_at": "2026-03-28T10:45:00Z"
}
```

---

## 6. document_summaries

Generated document summaries with cache invalidation.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Primary key |
| document_id | UUID | FK -> documents.id, NOT NULL, UNIQUE, INDEX | One summary per document |
| summary_text | TEXT | NOT NULL | Generated summary |
| key_topics | JSONB | NOT NULL, DEFAULT '[]' | List of key topic strings |
| content_hash | VARCHAR(64) | NOT NULL | SHA-256 of parsed content for cache check |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:**
- `uq_document_summaries_document_id` UNIQUE on `document_id`

**Relationships:**
- `document_id` -> `documents.id` (one-to-one)

**Example Record:**
```json
{
  "id": "12345678-abcd-ef01-2345-678901234567",
  "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "summary_text": "This Limited Partnership Agreement establishes Horizon Equity Partners IV as a Delaware limited partnership. The fund has a 10-year term with two optional 1-year extensions. Management fees are set at 2.0% of committed capital during the commitment period...",
  "key_topics": ["fund establishment", "management fees", "carried interest", "investor commitments", "fund term"],
  "content_hash": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
  "created_at": "2026-03-28T11:00:00Z"
}
```

---

## 7. bulk_jobs

Bulk processing job tracking.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Primary key |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | pending, processing, completed, failed, partial_failure |
| total_documents | INTEGER | NOT NULL | Total files in this job |
| processed_count | INTEGER | NOT NULL, DEFAULT 0 | Successfully processed |
| failed_count | INTEGER | NOT NULL, DEFAULT 0 | Failed documents |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| completed_at | TIMESTAMPTZ | NULLABLE | Set when job finishes |

**Indexes:**
- `ix_bulk_jobs_status` on `status`
- `ix_bulk_jobs_created_at` on `created_at DESC`

**Example Record:**
```json
{
  "id": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
  "status": "processing",
  "total_documents": 10,
  "processed_count": 6,
  "failed_count": 1,
  "created_at": "2026-03-28T12:00:00Z",
  "completed_at": null
}
```

---

## 8. bulk_job_documents

Per-document status within a bulk job.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Primary key |
| job_id | UUID | FK -> bulk_jobs.id, NOT NULL, INDEX | Parent job |
| document_id | UUID | FK -> documents.id, NOT NULL, INDEX | Associated document |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | pending, processing, completed, failed |
| error_message | TEXT | NULLABLE | Failure reason if status=failed |
| processing_time_ms | INTEGER | NULLABLE | Time taken in milliseconds |

**Indexes:**
- `ix_bulk_job_documents_job_id` on `job_id`
- `ix_bulk_job_documents_document_id` on `document_id`
- `uq_bulk_job_documents_job_doc` UNIQUE on `(job_id, document_id)`

**Relationships:**
- `job_id` -> `bulk_jobs.id` (many-to-one)
- `document_id` -> `documents.id` (many-to-one)

**Example Record:**
```json
{
  "id": "dddddddd-eeee-ffff-0000-111111111111",
  "job_id": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
  "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "error_message": null,
  "processing_time_ms": 12340
}
```

---

## 9. conversation_summaries

Persistent conversation summaries for long-term memory.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Primary key |
| session_id | VARCHAR(200) | NOT NULL, UNIQUE, INDEX | Chat session identifier |
| agent_type | VARCHAR(50) | NOT NULL | Agent that produced the summary (e.g., "rag_retriever") |
| summary | TEXT | NOT NULL | Conversation summary text |
| key_topics | JSONB | NOT NULL, DEFAULT '[]' | Key topics discussed |
| documents_discussed | JSONB | NOT NULL, DEFAULT '[]' | Document IDs referenced |
| queries_count | INTEGER | NOT NULL, DEFAULT 0 | Number of queries in session |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:**
- `uq_conversation_summaries_session_id` UNIQUE on `session_id`

**Example Record:**
```json
{
  "id": "cccccccc-dddd-eeee-ffff-000000000000",
  "session_id": "rag-chat-a1b2c3d4",
  "agent_type": "rag_retriever",
  "summary": "User queried management fee rates across multiple LPA documents. Compared Horizon Fund (2.0%) with Apex Fund (1.5%).",
  "key_topics": ["management fees", "fund comparison"],
  "documents_discussed": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890", "b2c3d4e5-f6a7-8901-bcde-f12345678901"],
  "queries_count": 4,
  "created_at": "2026-03-28T14:00:00Z",
  "updated_at": "2026-03-28T14:15:00Z"
}
```

---

## 10. memory_entries

Generic key-value store for long-term memory.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Primary key |
| namespace | VARCHAR(200) | NOT NULL, INDEX | Logical grouping (e.g., "user_preferences", "agent_state") |
| key | VARCHAR(500) | NOT NULL | Lookup key within namespace |
| data | JSONB | NOT NULL | Arbitrary JSON data |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:**
- `uq_memory_entries_ns_key` UNIQUE on `(namespace, key)`
- `ix_memory_entries_namespace` on `namespace`

**Example Record:**
```json
{
  "id": "eeeeeeee-ffff-0000-1111-222222222222",
  "namespace": "extraction_preferences",
  "key": "default_confidence_threshold",
  "data": {"threshold": "medium", "auto_approve_high": true},
  "created_at": "2026-03-28T09:00:00Z",
  "updated_at": "2026-03-28T09:00:00Z"
}
```

---

## Entity Relationship Diagram

```
document_categories
    |
    +--< extraction_schemas
    |       |
    |       +--< extraction_fields
    |                   |
    +--< documents      |
            |           |
            +--< extracted_values >--+
            |
            +--< document_summaries (1:1)
            |
            +--< bulk_job_documents >-- bulk_jobs

conversation_summaries (standalone)
memory_entries (standalone)
```

Legend: `--<` = one-to-many, `>--` = many-to-one

---

## Weaviate Collection (Not SQL)

**Collection:** `DocumentChunks`

| Property | Type | Description |
|----------|------|-------------|
| content | text | Chunk text content |
| document_id | text | UUID of source document |
| document_name | text | Original file name |
| document_category | text | Category name at ingestion time |
| file_name | text | Same as document_name |
| chunk_index | int | Sequential index within document |
| created_at | date | Ingestion timestamp |

**Vectorizer:** text2vec-openai
**Search:** Hybrid (BM25 + vector), configurable alpha parameter
