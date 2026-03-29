# API Contracts — PE Document Intelligence Platform

**Base URL:** `http://localhost:8000/api/v1`
**Content-Type:** `application/json` (unless multipart)
**Date format:** ISO 8601 (`2026-03-28T14:30:00Z`)
**ID format:** UUID v4

---

## Standard Error Response

All error responses follow this shape:

```json
{
  "detail": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE",
  "context": {}
}
```

| HTTP Status | Usage |
|-------------|-------|
| 400 | Validation error, invalid state transition, review gate failure |
| 404 | Resource not found |
| 409 | Conflict (e.g., duplicate file) |
| 422 | Request body validation failure (FastAPI default) |
| 500 | Internal server error |

---

## 1. Health

### GET /health

Check backend and dependency health.

**Request:** No parameters.

**Response 200:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "dependencies": {
    "database": "connected",
    "weaviate": "connected"
  }
}
```

---

## 2. Documents

### POST /documents/upload

Upload one or more document files.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `files` (one or more files)
- Accepted types: `.pdf`, `.docx`, `.xlsx`, `.png`, `.jpg`, `.tiff`

**Response 201 (new file):**
```json
{
  "id": "uuid",
  "file_name": "sample-lpa.pdf",
  "original_path": "data/upload/sample-lpa.pdf",
  "file_hash": "sha256hex",
  "status": "uploaded",
  "document_category_id": null,
  "file_type": "pdf",
  "file_size": 2048576,
  "created_at": "2026-03-28T10:00:00Z",
  "updated_at": "2026-03-28T10:00:00Z"
}
```

**Response 200 (duplicate — existing document returned):**
Same shape as above with existing document data.

**Response 422:** Invalid file type.

---

### GET /documents

List all documents.

**Request:**
- Query params (all optional):
  - `status` (string): filter by status
  - `category_id` (UUID): filter by category
  - `sort_by` (string): `created_at` (default), `file_name`, `status`
  - `sort_order` (string): `desc` (default), `asc`

**Response 200:**
```json
{
  "documents": [
    {
      "id": "uuid",
      "file_name": "sample-lpa.pdf",
      "status": "parsed",
      "document_category_id": "uuid | null",
      "file_type": "pdf",
      "file_size": 2048576,
      "created_at": "2026-03-28T10:00:00Z",
      "updated_at": "2026-03-28T10:05:00Z"
    }
  ],
  "total": 42
}
```

---

### GET /documents/:id

Get full document details.

**Request:**
- Path params: `id` (UUID)

**Response 200:**
```json
{
  "id": "uuid",
  "file_name": "sample-lpa.pdf",
  "original_path": "data/upload/sample-lpa.pdf",
  "parsed_path": "data/parsed/uuid.md",
  "file_hash": "sha256hex",
  "status": "classified",
  "document_category_id": "uuid",
  "file_type": "pdf",
  "file_size": 2048576,
  "created_at": "2026-03-28T10:00:00Z",
  "updated_at": "2026-03-28T10:30:00Z"
}
```

**Response 404:** Document not found.

---

### DELETE /documents/:id

Delete a document and its associated files.

**Request:**
- Path params: `id` (UUID)

**Response 204:** No content.

**Response 404:** Document not found.

---

## 3. Parse

### POST /parse/:id

Trigger document parsing via Reducto.

**Request:**
- Path params: `id` (UUID)

**Response 200 (already parsed, hash unchanged):**
```json
{
  "document_id": "uuid",
  "status": "parsed",
  "content": "# Document Title\n\nParsed markdown content...",
  "skipped": true,
  "message": "File hash unchanged, returning cached parse result"
}
```

**Response 201 (newly parsed):**
```json
{
  "document_id": "uuid",
  "status": "parsed",
  "content": "# Document Title\n\nParsed markdown content...",
  "skipped": false
}
```

**Response 400:** Invalid state transition (document not in `uploaded` state).

**Response 500:** Reducto API failure (after 3 retries).

---

### GET /parse/:id/content

Get parsed markdown content.

**Request:**
- Path params: `id` (UUID)

**Response 200:**
```json
{
  "document_id": "uuid",
  "content": "# Document Title\n\nParsed markdown content...",
  "status": "parsed"
}
```

**Response 404:** No parsed content exists.

---

### PUT /parse/:id/content

Save edited markdown content.

**Request:**
- Path params: `id` (UUID)
- Body:
```json
{
  "content": "# Edited Document Title\n\nEdited content..."
}
```

**Response 200:**
```json
{
  "document_id": "uuid",
  "status": "edited",
  "content_length": 4523
}
```

**Response 400:** Invalid state transition.

---

## 4. Classify

### POST /classify/:id

Classify a document against user-defined categories.

**Request:**
- Path params: `id` (UUID)

**Response 200:**
```json
{
  "document_id": "uuid",
  "category_id": "uuid",
  "category_name": "LPA",
  "reasoning": "The document contains typical LPA clauses including...",
  "status": "classified"
}
```

**Response 400:** Invalid state transition (document must be `parsed` or `edited`).

---

## 5. Extract

### POST /extract/:id

Trigger field extraction and confidence judging.

**Request:**
- Path params: `id` (UUID)

**Response 201:**
```json
{
  "document_id": "uuid",
  "status": "extracted",
  "results": [
    {
      "id": "uuid",
      "field_name": "fund_name",
      "display_name": "Fund Name",
      "extracted_value": "Horizon Equity Partners IV",
      "source_text": "...hereby establishes Horizon Equity Partners IV, a Delaware...",
      "confidence": "high",
      "confidence_reasoning": "Source text explicitly names the fund in the establishment clause.",
      "requires_review": false,
      "reviewed": false
    },
    {
      "id": "uuid",
      "field_name": "fund_term",
      "display_name": "Fund Term",
      "extracted_value": "10 years",
      "source_text": "...initial term...not to exceed ten years...subject to two one-year extensions...",
      "confidence": "low",
      "confidence_reasoning": "Multiple possible interpretations: base term of 10 years with optional extensions to 12 years.",
      "requires_review": true,
      "reviewed": false
    }
  ],
  "requires_review_count": 1
}
```

**Response 400:** Invalid state transition (document must be `classified`).

---

### GET /extract/:id/results

Get extraction results for a document.

**Request:**
- Path params: `id` (UUID)

**Response 200:**
```json
{
  "document_id": "uuid",
  "results": [
    {
      "id": "uuid",
      "field_name": "fund_name",
      "display_name": "Fund Name",
      "extracted_value": "Horizon Equity Partners IV",
      "source_text": "...hereby establishes Horizon Equity Partners IV...",
      "confidence": "high",
      "confidence_reasoning": "Source text explicitly names the fund.",
      "requires_review": false,
      "reviewed": false
    }
  ],
  "requires_review_count": 0,
  "all_reviewed": true
}
```

**Response 404:** No extraction results exist for this document.

---

### PUT /extract/:id/results

Update extracted values (review/edit fields).

**Request:**
- Path params: `id` (UUID)
- Body:
```json
{
  "updates": [
    {
      "field_id": "uuid",
      "extracted_value": "10 years (with 2x1-year extensions)",
      "reviewed": true
    }
  ]
}
```

**Response 200:**
```json
{
  "document_id": "uuid",
  "updated_count": 1,
  "requires_review_count": 0,
  "all_reviewed": true,
  "can_proceed": true
}
```

**Response 400 (review gate failure):**
```json
{
  "detail": "Cannot proceed: 2 fields require review",
  "error_code": "REVIEW_GATE_FAILED",
  "context": {
    "unreviewed_fields": ["fund_term", "governing_law"]
  }
}
```

---

## 6. Summarize

### POST /summarize/:id

Generate or regenerate a document summary.

**Request:**
- Path params: `id` (UUID)

**Response 201 (new summary):**
```json
{
  "document_id": "uuid",
  "summary": "This Limited Partnership Agreement establishes Horizon Equity Partners IV...",
  "key_topics": ["fund establishment", "management fees", "carried interest", "investor commitments"],
  "status": "summarized",
  "cached": false
}
```

**Response 200 (cached, content hash unchanged):**
```json
{
  "document_id": "uuid",
  "summary": "This Limited Partnership Agreement establishes...",
  "key_topics": ["fund establishment", "management fees"],
  "status": "summarized",
  "cached": true
}
```

**Response 400:** Invalid state transition (document must be `extracted`).

---

### GET /summarize/:id

Get existing summary.

**Request:**
- Path params: `id` (UUID)

**Response 200:**
```json
{
  "document_id": "uuid",
  "summary": "This Limited Partnership Agreement establishes...",
  "key_topics": ["fund establishment", "management fees"],
  "content_hash": "sha256hex",
  "created_at": "2026-03-28T11:00:00Z"
}
```

**Response 404:** No summary exists for this document.

---

## 7. Ingest

### POST /ingest/:id

Ingest document into Weaviate for RAG retrieval.

**Request:**
- Path params: `id` (UUID)

**Response 200:**
```json
{
  "document_id": "uuid",
  "status": "ingested",
  "chunks_created": 24,
  "collection": "DocumentChunks"
}
```

**Response 400:** Invalid state transition (document must be `summarized`).

---

## 8. RAG Query

### POST /rag/query

Query ingested documents using RAG.

**Request:**
- Body:
```json
{
  "query": "What is the management fee rate for Horizon fund?",
  "scope": "single_document",
  "scope_id": "uuid",
  "search_mode": "hybrid",
  "top_k": 5
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| query | string | yes | - | User's question |
| scope | enum | yes | - | `single_document`, `all`, `by_category` |
| scope_id | UUID | conditional | - | Required when scope is `single_document` or `by_category` |
| search_mode | enum | no | `hybrid` | `semantic`, `keyword`, `hybrid` |
| top_k | integer | no | 5 | Number of chunks to retrieve |

**Response 200:**
```json
{
  "answer": "The management fee rate for Horizon Equity Partners IV is 2% of committed capital during the commitment period...",
  "citations": [
    {
      "chunk_text": "The Management Fee shall be equal to 2.0% per annum of aggregate Commitments...",
      "document_name": "sample-lpa.pdf",
      "document_id": "uuid",
      "chunk_index": 14,
      "relevance_score": 0.92
    }
  ],
  "search_mode": "hybrid",
  "chunks_retrieved": 5
}
```

---

## 9. Config — Categories

### GET /config/categories

List all document categories.

**Request:** No parameters.

**Response 200:**
```json
{
  "categories": [
    {
      "id": "uuid",
      "name": "LPA",
      "description": "Limited Partnership Agreements",
      "classification_criteria": "Documents that establish a limited partnership fund...",
      "created_at": "2026-03-28T09:00:00Z",
      "updated_at": "2026-03-28T09:00:00Z"
    }
  ]
}
```

---

### POST /config/categories

Create a new category.

**Request:**
- Body:
```json
{
  "name": "Subscription Agreement",
  "description": "Investor subscription documents",
  "classification_criteria": "Documents through which investors commit capital to a fund..."
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "name": "Subscription Agreement",
  "description": "Investor subscription documents",
  "classification_criteria": "Documents through which investors commit capital...",
  "created_at": "2026-03-28T09:15:00Z",
  "updated_at": "2026-03-28T09:15:00Z"
}
```

---

### PUT /config/categories/:id

Update a category.

**Request:**
- Path params: `id` (UUID)
- Body:
```json
{
  "name": "LPA",
  "description": "Updated description",
  "classification_criteria": "Updated criteria..."
}
```

**Response 200:** Updated category object (same shape as POST response).

**Response 404:** Category not found.

---

### DELETE /config/categories/:id

Delete a category.

**Request:**
- Path params: `id` (UUID)

**Response 204:** No content.

**Response 400:** Category has assigned documents.
```json
{
  "detail": "Cannot delete category with assigned documents",
  "error_code": "CATEGORY_IN_USE",
  "context": {
    "document_count": 5
  }
}
```

**Response 404:** Category not found.

---

## 10. Config — Extraction Fields

### GET /config/categories/:id/fields

List extraction fields for a category.

**Request:**
- Path params: `id` (UUID) — category ID

**Response 200:**
```json
{
  "category_id": "uuid",
  "category_name": "LPA",
  "schema_version": 1,
  "fields": [
    {
      "id": "uuid",
      "field_name": "fund_name",
      "display_name": "Fund Name",
      "description": "The official name of the fund",
      "examples": "Horizon Equity Partners IV, Apex Growth Fund III",
      "data_type": "string",
      "required": true,
      "sort_order": 1
    }
  ]
}
```

**Response 404:** Category not found.

---

### POST /config/categories/:id/fields

Create or update extraction fields for a category.

**Request:**
- Path params: `id` (UUID) — category ID
- Body:
```json
{
  "fields": [
    {
      "field_name": "fund_name",
      "display_name": "Fund Name",
      "description": "The official name of the fund",
      "examples": "Horizon Equity Partners IV, Apex Growth Fund III",
      "data_type": "string",
      "required": true,
      "sort_order": 1
    },
    {
      "field_name": "management_fee_rate",
      "display_name": "Management Fee Rate",
      "description": "Annual management fee as percentage of committed capital",
      "examples": "2.0%, 1.5%",
      "data_type": "percentage",
      "required": true,
      "sort_order": 2
    }
  ]
}
```

**Response 200:**
```json
{
  "category_id": "uuid",
  "schema_version": 2,
  "fields_created": 2,
  "fields_updated": 0
}
```

**Response 404:** Category not found.

---

## 11. Bulk Processing

### POST /bulk/upload

Start a new bulk processing job.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `files` (multiple files)

**Response 201:**
```json
{
  "job_id": "uuid",
  "status": "pending",
  "total_documents": 10,
  "documents": [
    {
      "document_id": "uuid",
      "file_name": "doc-001.pdf",
      "status": "pending"
    }
  ],
  "created_at": "2026-03-28T12:00:00Z"
}
```

---

### GET /bulk/jobs

List all bulk jobs.

**Request:**
- Query params (optional):
  - `status` (string): filter by job status

**Response 200:**
```json
{
  "jobs": [
    {
      "id": "uuid",
      "status": "processing",
      "total_documents": 10,
      "processed_count": 6,
      "failed_count": 1,
      "created_at": "2026-03-28T12:00:00Z",
      "completed_at": null
    }
  ]
}
```

---

### GET /bulk/jobs/:id

Get bulk job details with per-document progress.

**Request:**
- Path params: `id` (UUID)

**Response 200:**
```json
{
  "id": "uuid",
  "status": "processing",
  "total_documents": 10,
  "processed_count": 6,
  "failed_count": 1,
  "created_at": "2026-03-28T12:00:00Z",
  "completed_at": null,
  "documents": [
    {
      "document_id": "uuid",
      "file_name": "doc-001.pdf",
      "status": "completed",
      "error_message": null,
      "processing_time_ms": 12340
    },
    {
      "document_id": "uuid",
      "file_name": "doc-003.pdf",
      "status": "failed",
      "error_message": "Reducto parsing failed: corrupted PDF",
      "processing_time_ms": 2100
    }
  ]
}
```

**Response 404:** Job not found.
