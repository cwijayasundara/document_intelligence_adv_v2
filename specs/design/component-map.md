# Component Map — PE Document Intelligence Platform

Maps every story ID to the specific files that will be created or modified.

---

## Epic 1 — Foundation Infrastructure

| Story | Title | Files Created / Modified |
|-------|-------|--------------------------|
| E1-S1 | Database Types & ORM Models | `backend/src/db/models.py` (create), `backend/src/db/enums.py` (create), `backend/src/db/__init__.py` (create) |
| E1-S2 | Application Configuration | `backend/src/config/__init__.py` (create), `backend/src/config/settings.py` (create), `backend/config.yml` (create), `backend/.env.example` (create) |
| E1-S3 | Database Connection & Migrations | `backend/src/db/connection.py` (create), `backend/alembic.ini` (create), `backend/alembic/env.py` (create), `backend/alembic/versions/001_initial_schema.py` (create) |
| E1-S4 | FastAPI Application Factory + Health | `backend/src/api/app.py` (create), `backend/src/api/__init__.py` (create), `backend/src/api/dependencies.py` (create), `backend/src/api/routers/health.py` (create), `backend/src/api/routers/__init__.py` (create), `backend/src/api/schemas/common.py` (create), `backend/src/api/schemas/__init__.py` (create), `backend/src/main.py` (create), `backend/src/__init__.py` (create) |

---

## Epic 2 — Document Upload & Parsing

| Story | Title | Files Created / Modified |
|-------|-------|--------------------------|
| E2-S1 | Document Repository + Upload Service + API | `backend/src/db/repositories/documents.py` (create), `backend/src/db/repositories/__init__.py` (create), `backend/src/services/document_service.py` (create), `backend/src/services/__init__.py` (create), `backend/src/storage/local.py` (create), `backend/src/storage/__init__.py` (create), `backend/src/api/routers/documents.py` (create), `backend/src/api/schemas/documents.py` (create) |
| E2-S2 | Document State Machine | `backend/src/services/state_machine.py` (create), `backend/src/services/document_service.py` (modify) |
| E2-S3 | Reducto Parser + Parse/Edit API | `backend/src/parser/reducto.py` (create), `backend/src/parser/__init__.py` (create), `backend/src/services/parse_service.py` (create), `backend/src/api/routers/parse.py` (create), `backend/src/api/schemas/parse.py` (create) |

---

## Epic 3 — Agent Framework & Memory

| Story | Title | Files Created / Modified |
|-------|-------|--------------------------|
| E3-S1 | DeepAgent Orchestrator Scaffold | `backend/src/agents/__init__.py` (create), `backend/src/agents/orchestrator.py` (create), `backend/src/agents/tools/__init__.py` (create), `backend/src/agents/tools/document_tools.py` (create), `backend/src/agents/schemas/__init__.py` (create) |
| E3-S2 | PII Filtering Middleware | `backend/src/agents/middleware/__init__.py` (create), `backend/src/agents/middleware/pii_filter.py` (create), `backend/src/agents/orchestrator.py` (modify) |
| E3-S3 | Short-Term Memory | `backend/src/agents/memory/__init__.py` (create), `backend/src/agents/memory/short_term.py` (create) |
| E3-S4 | Long-Term Memory (PostgreSQL) | `backend/src/agents/memory/long_term.py` (create), `backend/src/db/repositories/memory.py` (create), `backend/src/db/models.py` (modify — add conversation_summaries, memory_entries models) |

---

## Epic 4 — Classification & Config

| Story | Title | Files Created / Modified |
|-------|-------|--------------------------|
| E4-S1 | Category & Extraction Schema CRUD | `backend/src/db/repositories/categories.py` (create), `backend/src/db/repositories/extraction.py` (create), `backend/src/api/routers/config.py` (create), `backend/src/api/schemas/config.py` (create) |
| E4-S2 | Classifier Subagent | `backend/src/agents/classifier.py` (create), `backend/src/agents/tools/category_tools.py` (create), `backend/src/agents/schemas/classification.py` (create), `backend/src/agents/orchestrator.py` (modify — register classifier) |
| E4-S3 | Classification API Endpoint | `backend/src/api/routers/classify.py` (create), `backend/src/api/schemas/classify.py` (create), `backend/src/services/classify_service.py` (create) |

---

## Epic 5 — Extraction & Confidence Judging

| Story | Title | Files Created / Modified |
|-------|-------|--------------------------|
| E5-S1 | Extractor Subagent | `backend/src/agents/extractor.py` (create), `backend/src/agents/schemas/extraction.py` (create), `backend/src/agents/orchestrator.py` (modify — register extractor) |
| E5-S2 | Judge Subagent | `backend/src/agents/judge.py` (create), `backend/src/agents/tools/extraction_tools.py` (create), `backend/src/agents/schemas/judge.py` (create), `backend/src/agents/orchestrator.py` (modify — register judge) |
| E5-S3 | Extraction API + Review Gate | `backend/src/db/repositories/extracted_values.py` (create), `backend/src/services/extract_service.py` (create), `backend/src/api/routers/extract.py` (create), `backend/src/api/schemas/extract.py` (create) |

---

## Epic 6 — Summarization & RAG

| Story | Title | Files Created / Modified |
|-------|-------|--------------------------|
| E6-S1 | Summarizer Subagent + API | `backend/src/agents/summarizer.py` (create), `backend/src/agents/schemas/summary.py` (create), `backend/src/db/repositories/summaries.py` (create), `backend/src/services/summarize_service.py` (create), `backend/src/api/routers/summarize.py` (create), `backend/src/api/schemas/summarize.py` (create), `backend/src/agents/orchestrator.py` (modify — register summarizer) |
| E6-S2 | Weaviate Client + Chunking + Ingestion | `backend/src/rag/__init__.py` (create), `backend/src/rag/weaviate_client.py` (create), `backend/src/rag/chunker.py` (create), `backend/src/rag/ingestion.py` (create), `backend/src/services/ingest_service.py` (create), `backend/src/api/routers/ingest.py` (create) |
| E6-S3 | RAG Retriever Subagent + Query API | `backend/src/agents/rag_retriever.py` (create), `backend/src/agents/tools/search_tools.py` (create), `backend/src/rag/search.py` (create), `backend/src/api/routers/rag.py` (create), `backend/src/api/schemas/rag.py` (create), `backend/src/agents/orchestrator.py` (modify — register rag_retriever) |

---

## Epic 7 — Frontend Core

| Story | Title | Files Created / Modified |
|-------|-------|--------------------------|
| E7-S1 | Frontend App Shell, Routing, API Client | `frontend/src/main.tsx` (create), `frontend/src/App.tsx` (create), `frontend/src/lib/api/client.ts` (create), `frontend/src/lib/config.ts` (create), `frontend/src/components/ui/Layout.tsx` (create), `frontend/src/components/ui/Sidebar.tsx` (create), `frontend/src/components/ui/PageHeader.tsx` (create), `frontend/src/types/common.ts` (create), `frontend/package.json` (create), `frontend/vite.config.ts` (create), `frontend/tailwind.config.ts` (create), `frontend/tsconfig.json` (create), `frontend/tsconfig.app.json` (create), `frontend/tsconfig.node.json` (create), `frontend/index.html` (create) |
| E7-S2 | Dashboard — Document List with Status | `frontend/src/pages/DashboardPage.tsx` (create), `frontend/src/components/documents/DocumentList.tsx` (create), `frontend/src/components/documents/DocumentRow.tsx` (create), `frontend/src/components/documents/DocumentStatusBadge.tsx` (create), `frontend/src/components/ui/EmptyState.tsx` (create), `frontend/src/hooks/useDocuments.ts` (create), `frontend/src/lib/api/documents.ts` (create), `frontend/src/types/document.ts` (create) |
| E7-S3 | Upload Page with Drag-Drop | `frontend/src/pages/UploadPage.tsx` (create), `frontend/src/components/upload/UploadDropzone.tsx` (create), `frontend/src/components/upload/UploadProgress.tsx` (create), `frontend/src/components/upload/FileTypeIcon.tsx` (create), `frontend/src/hooks/useDocuments.ts` (modify — add upload mutation) |
| E7-S4 | Parse/Edit Page with TipTap Split View | `frontend/src/pages/ParsePage.tsx` (create), `frontend/src/components/parse/ParseView.tsx` (create), `frontend/src/components/parse/RichTextEditor.tsx` (create), `frontend/src/components/parse/SplitView.tsx` (create), `frontend/src/hooks/useParse.ts` (create), `frontend/src/lib/api/parse.ts` (create), `frontend/src/types/parse.ts` (create) |

---

## Epic 8 — Frontend AI & Config

| Story | Title | Files Created / Modified |
|-------|-------|--------------------------|
| E8-S1 | Config Management Pages | `frontend/src/pages/CategoriesPage.tsx` (create), `frontend/src/pages/ExtractionFieldsPage.tsx` (create), `frontend/src/components/config/CategoryManager.tsx` (create), `frontend/src/components/config/CategoryFormModal.tsx` (create), `frontend/src/components/config/ExtractionFieldEditor.tsx` (create), `frontend/src/components/config/FieldFormModal.tsx` (create), `frontend/src/hooks/useCategories.ts` (create), `frontend/src/hooks/useExtractionFields.ts` (create), `frontend/src/lib/api/config.ts` (create), `frontend/src/types/config.ts` (create), `frontend/src/components/ui/Modal.tsx` (create) |
| E8-S2 | Classification Page with Override | `frontend/src/pages/ClassifyPage.tsx` (create), `frontend/src/components/classify/ClassificationResult.tsx` (create), `frontend/src/components/classify/CategoryOverride.tsx` (create), `frontend/src/hooks/useClassify.ts` (create), `frontend/src/lib/api/classify.ts` (create), `frontend/src/types/classify.ts` (create) |
| E8-S3 | Extraction Results 3-Column View | `frontend/src/pages/ExtractPage.tsx` (create), `frontend/src/components/extract/ExtractionResultsTable.tsx` (create), `frontend/src/components/extract/ConfidenceBadge.tsx` (create), `frontend/src/components/extract/ConfidenceReviewPanel.tsx` (create), `frontend/src/components/extract/InlineFieldEditor.tsx` (create), `frontend/src/hooks/useExtract.ts` (create), `frontend/src/lib/api/extract.ts` (create), `frontend/src/types/extract.ts` (create) |
| E8-S4 | Summary Page with Regenerate | `frontend/src/pages/SummaryPage.tsx` (create), `frontend/src/components/summary/SummaryView.tsx` (create), `frontend/src/components/summary/KeyTopicTags.tsx` (create), `frontend/src/hooks/useSummarize.ts` (create), `frontend/src/hooks/useIngest.ts` (create), `frontend/src/lib/api/summarize.ts` (create), `frontend/src/lib/api/ingest.ts` (create), `frontend/src/types/summary.ts` (create) |
| E8-S5 | RAG Chat Page with Citations | `frontend/src/pages/ChatPage.tsx` (create), `frontend/src/components/chat/ChatInterface.tsx` (create), `frontend/src/components/chat/ChatMessage.tsx` (create), `frontend/src/components/chat/CitationCard.tsx` (create), `frontend/src/components/chat/ScopeSelector.tsx` (create), `frontend/src/components/chat/SearchModeToggle.tsx` (create), `frontend/src/hooks/useRag.ts` (create), `frontend/src/lib/api/rag.ts` (create), `frontend/src/types/rag.ts` (create) |

---

## Epic 9 — Bulk Processing

| Story | Title | Files Created / Modified |
|-------|-------|--------------------------|
| E9-S1 | LangGraph Bulk State Graph | `backend/src/bulk/__init__.py` (create), `backend/src/bulk/state_graph.py` (create), `backend/src/bulk/state.py` (create), `backend/src/bulk/nodes/__init__.py` (create), `backend/src/bulk/nodes/parse_node.py` (create), `backend/src/bulk/nodes/classify_node.py` (create), `backend/src/bulk/nodes/extract_node.py` (create), `backend/src/bulk/nodes/judge_node.py` (create), `backend/src/bulk/nodes/summarize_node.py` (create), `backend/src/bulk/nodes/ingest_node.py` (create), `backend/src/bulk/nodes/finalize_node.py` (create) |
| E9-S2 | Bulk Job Repository + API | `backend/src/db/repositories/bulk_jobs.py` (create), `backend/src/bulk/service.py` (create), `backend/src/api/routers/bulk.py` (create), `backend/src/api/schemas/bulk.py` (create) |
| E9-S3 | Bulk Upload + Dashboard UI | `frontend/src/pages/BulkPage.tsx` (create), `frontend/src/components/bulk/BulkJobDashboard.tsx` (create), `frontend/src/components/bulk/BulkJobRow.tsx` (create), `frontend/src/components/bulk/BulkProgressBar.tsx` (create), `frontend/src/components/bulk/BulkUploadZone.tsx` (create), `frontend/src/hooks/useBulk.ts` (create), `frontend/src/lib/api/bulk.ts` (create), `frontend/src/types/bulk.ts` (create) |

---

## Cross-Cutting Files

These files are created once and modified across multiple stories:

| File | Created By | Modified By |
|------|-----------|-------------|
| `backend/src/agents/orchestrator.py` | E3-S1 | E3-S2, E4-S2, E5-S1, E5-S2, E6-S1, E6-S3 |
| `backend/src/db/models.py` | E1-S1 | E3-S4 |
| `backend/src/services/document_service.py` | E2-S1 | E2-S2 |
| `frontend/src/hooks/useDocuments.ts` | E7-S2 | E7-S3 |
| `docker-compose.yml` | E1-S3 | — |
| `init.sh` | E1-S2 | — |
