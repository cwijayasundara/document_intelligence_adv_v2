# Test Plan -- PE Document Intelligence Platform

## Scope

Stories covered: E1-S1 through E9-S3 (32 stories total across 9 epics)

### Epics

| Epic | Name | Stories |
|------|------|---------|
| E1 | Foundation Infrastructure | E1-S1, E1-S2, E1-S3, E1-S4 |
| E2 | Document Upload & Parsing | E2-S1, E2-S2, E2-S3 |
| E3 | Agent Framework & Memory | E3-S1, E3-S2, E3-S3, E3-S4 |
| E4 | Classification & Config Management | E4-S1, E4-S2, E4-S3 |
| E5 | Extraction & Confidence Judging | E5-S1, E5-S2, E5-S3 |
| E6 | Summarization & RAG | E6-S1, E6-S2, E6-S3 |
| E7 | Frontend Core | E7-S1, E7-S2, E7-S3, E7-S4 |
| E8 | Frontend AI & Config | E8-S1, E8-S2, E8-S3, E8-S4, E8-S5 |
| E9 | Bulk Processing | E9-S1, E9-S2, E9-S3 |

### Out of Scope

- Load testing and performance benchmarking
- Security penetration testing
- Multi-tenant isolation testing (single-tenant system)
- Mobile / responsive layout testing

## Test Environment

| Component | Technology | Address |
|-----------|------------|---------|
| Backend API | FastAPI (Python 3.13, uvicorn) | http://localhost:8000 |
| Frontend UI | React 19 + Vite (TypeScript) | http://localhost:5173 |
| Primary DB | PostgreSQL 16 | localhost:5432 |
| Vector DB | Weaviate | localhost:8080 |
| Unit test runner (backend) | pytest | N/A |
| Unit test runner (frontend) | vitest | N/A |
| E2E framework | Playwright (Chromium) | N/A |
| Container orchestration | docker-compose | N/A |

### Test Database Strategy

- Integration and E2E tests use a dedicated `pe_doc_intel_test` PostgreSQL database
- Alembic migrations run against the test database before each test suite
- Each integration test function uses a database transaction that is rolled back after the test
- Weaviate test collection uses a `DocumentChunks_test` collection prefix, cleared between test runs

## Test Levels

### Level 1: Unit Tests (pytest / vitest)

**Backend (pytest)**
- ORM model definitions and enum values (E1-S1)
- Configuration loading and validation (E1-S2)
- State machine transition logic (E2-S2)
- PII filtering regex patterns (E3-S2)
- Short-term memory trimming logic (E3-S3)
- Dynamic Pydantic model builder (E5-S1)
- Confidence scoring criteria (E5-S2)

**Frontend (vitest)**
- DocumentStatusBadge component renders correct colors (E7-S2)
- API client request/response transformers (E7-S1)
- Confidence badge rendering logic (E8-S3)
- Scope selector state management (E8-S5)

### Level 2: Integration Tests (pytest with real DB)

- Document repository CRUD operations (E2-S1)
- Document upload with file dedup via SHA-256 (E2-S1)
- Parse API round-trip: upload -> parse -> retrieve content (E2-S3)
- Category and extraction schema CRUD (E4-S1)
- Classification API with state machine enforcement (E4-S3)
- Extraction API with judge pipeline and review gate (E5-S3)
- Summarization with content hash caching (E6-S1)
- Weaviate ingestion and hybrid search (E6-S2, E6-S3)
- Bulk job creation and per-document status tracking (E9-S2)
- Long-term memory CRUD and upsert semantics (E3-S4)

### Level 3: E2E Tests (Playwright)

- Dashboard document list with status badges (E7-S2)
- Upload page with drag-drop and duplicate detection (E7-S3)
- Parse/Edit page with TipTap editor (E7-S4)
- Config management: categories and extraction fields (E8-S1)
- Classification page with override (E8-S2)
- Extraction results with review gate (E8-S3)
- Summary page with regenerate (E8-S4)
- RAG chat page with citations (E8-S5)
- Bulk upload and dashboard (E9-S3)

## Story Coverage Matrix

| Story | Unit | Integration | E2E | AC Count | TC Count |
|-------|------|-------------|-----|----------|----------|
| E1-S1 | Y | - | - | 6 | 6 |
| E1-S2 | Y | - | - | 5 | 5 |
| E1-S3 | - | Y | - | 5 | 4 |
| E1-S4 | - | Y | - | 5 | 4 |
| E2-S1 | - | Y | - | 6 | 8 |
| E2-S2 | Y | Y | - | 4 | 6 |
| E2-S3 | - | Y | - | 6 | 7 |
| E3-S1 | Y | - | - | 5 | 4 |
| E3-S2 | Y | - | - | 5 | 6 |
| E3-S3 | Y | - | - | 5 | 5 |
| E3-S4 | - | Y | - | 5 | 5 |
| E4-S1 | - | Y | - | 7 | 8 |
| E4-S2 | Y | Y | - | 5 | 5 |
| E4-S3 | - | Y | - | 5 | 5 |
| E5-S1 | Y | - | - | 5 | 4 |
| E5-S2 | Y | - | - | 5 | 4 |
| E5-S3 | - | Y | - | 6 | 8 |
| E6-S1 | - | Y | - | 6 | 6 |
| E6-S2 | - | Y | - | 6 | 5 |
| E6-S3 | - | Y | - | 5 | 5 |
| E7-S1 | Y | - | - | 5 | 4 |
| E7-S2 | Y | - | Y | 5 | 6 |
| E7-S3 | - | - | Y | 5 | 6 |
| E7-S4 | - | - | Y | 5 | 6 |
| E8-S1 | - | - | Y | 5 | 7 |
| E8-S2 | - | - | Y | 5 | 6 |
| E8-S3 | - | - | Y | 6 | 8 |
| E8-S4 | - | - | Y | 5 | 6 |
| E8-S5 | - | - | Y | 5 | 6 |
| E9-S1 | Y | Y | - | 5 | 5 |
| E9-S2 | - | Y | - | 5 | 5 |
| E9-S3 | - | - | Y | 5 | 6 |
| **Total** | | | | **166** | **180** |

## Pass/Fail Criteria

- All 180 test cases must pass
- Backend unit + integration coverage >= 80% (measured by pytest-cov)
- Frontend unit coverage >= 80% (measured by vitest c8)
- Zero critical or high-severity defects remaining
- All E2E Playwright tests pass on Desktop Chrome

## Risk Areas

| Risk | Mitigation |
|------|------------|
| Reducto Cloud API availability during tests | Mock Reducto client in unit/integration tests; E2E tests use pre-parsed fixtures |
| OpenAI API rate limits during classification/extraction/judge tests | Mock LLM responses for unit tests; use low-cost model for integration; E2E uses pre-seeded data |
| Weaviate vectorizer dependency on OpenAI embeddings | Use deterministic test embeddings or mock vectorizer in unit tests |
| PII filtering false positives on fund names containing person-like strings | Dedicated test cases with edge-case fund names (e.g., "John Smith Capital Partners") |
| Bulk pipeline concurrency race conditions | Integration tests exercise concurrent document processing; verify per-document error isolation |
| TipTap editor DOM interactions in Playwright | Use data-testid attributes on editor container; avoid testing rich-text internals |
| Flaky tests from network timing | Use Playwright auto-wait; explicit waitForResponse on API calls; no hardcoded timeouts |

## Test Execution Order

Tests should be run in this order to catch foundational failures first:

1. Backend unit tests (`cd backend && pytest tests/unit/`)
2. Backend integration tests (`cd backend && pytest tests/integration/`)
3. Frontend unit tests (`cd frontend && npm run test`)
4. E2E tests (`npx playwright test`)

## CI Integration Notes

- Backend tests require PostgreSQL and Weaviate services (use docker-compose test profile)
- Frontend unit tests require no external services
- E2E tests require all services running (backend, frontend, PostgreSQL, Weaviate)
- Playwright traces and screenshots saved to `e2e/test-results/` on failure
