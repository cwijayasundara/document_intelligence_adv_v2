# Folder Structure — PE Document Intelligence Platform

```
document_intelligence_adv_v2/
|
+-- backend/                            # Python FastAPI backend
|   +-- src/                            # Application source code
|   |   +-- __init__.py                 # Package init
|   |   +-- main.py                     # Uvicorn entrypoint, app startup/shutdown
|   |   |
|   |   +-- api/                        # FastAPI API layer
|   |   |   +-- __init__.py
|   |   |   +-- app.py                  # FastAPI app factory, CORS, exception handlers
|   |   |   +-- dependencies.py         # Shared dependencies (DB session, agent instance)
|   |   |   +-- routers/                # Route modules, one per domain
|   |   |   |   +-- __init__.py
|   |   |   |   +-- documents.py        # /documents — upload, list, get, delete
|   |   |   |   +-- parse.py            # /parse — trigger, get content, edit
|   |   |   |   +-- classify.py         # /classify — trigger classification
|   |   |   |   +-- extract.py          # /extract — trigger, get results, update
|   |   |   |   +-- summarize.py        # /summarize — generate, get summary
|   |   |   |   +-- ingest.py           # /ingest — ingest into Weaviate
|   |   |   |   +-- rag.py              # /rag — query endpoint
|   |   |   |   +-- config.py           # /config — categories, fields CRUD
|   |   |   |   +-- bulk.py             # /bulk — upload, jobs, job detail
|   |   |   |   +-- health.py           # /health — health check
|   |   |   +-- schemas/                # Pydantic request/response schemas
|   |   |       +-- __init__.py
|   |   |       +-- documents.py        # Document request/response models
|   |   |       +-- parse.py            # Parse-related models
|   |   |       +-- classify.py         # Classification models
|   |   |       +-- extract.py          # Extraction models
|   |   |       +-- summarize.py        # Summary models
|   |   |       +-- rag.py              # RAG query/response models
|   |   |       +-- config.py           # Category and field models
|   |   |       +-- bulk.py             # Bulk job models
|   |   |       +-- common.py           # Shared base models, error response
|   |   |
|   |   +-- db/                         # Database layer
|   |   |   +-- __init__.py
|   |   |   +-- connection.py           # Async engine, session factory, get_session
|   |   |   +-- models.py              # SQLAlchemy 2.0 ORM models (all 10 tables)
|   |   |   +-- enums.py               # DocumentStatus, BulkJobStatus enums
|   |   |   +-- repositories/           # Repository classes (async CRUD)
|   |   |       +-- __init__.py
|   |   |       +-- documents.py        # DocumentRepository
|   |   |       +-- categories.py       # CategoryRepository
|   |   |       +-- extraction.py       # ExtractionSchemaRepository, ExtractionFieldRepository
|   |   |       +-- extracted_values.py # ExtractedValuesRepository
|   |   |       +-- summaries.py        # SummaryRepository
|   |   |       +-- bulk_jobs.py        # BulkJobRepository
|   |   |       +-- memory.py           # ConversationSummaryRepository, MemoryEntryRepository
|   |   |
|   |   +-- agents/                     # DeepAgents layer
|   |   |   +-- __init__.py
|   |   |   +-- orchestrator.py         # create_deep_agent orchestrator, singleton factory
|   |   |   +-- classifier.py           # Classifier subagent definition + tools
|   |   |   +-- extractor.py            # Extractor subagent + dynamic Pydantic models
|   |   |   +-- judge.py                # Judge subagent + confidence scoring
|   |   |   +-- summarizer.py           # Summarizer subagent
|   |   |   +-- rag_retriever.py        # RAG retriever subagent
|   |   |   +-- middleware/             # Agent middleware
|   |   |   |   +-- __init__.py
|   |   |   |   +-- pii_filter.py       # PII redaction pre-model callback
|   |   |   +-- memory/                 # Memory layer
|   |   |   |   +-- __init__.py
|   |   |   |   +-- short_term.py       # ShortTermMemory (in-memory LRU)
|   |   |   |   +-- long_term.py        # PostgresLongTermMemory (DB-backed)
|   |   |   +-- tools/                  # Agent tool definitions
|   |   |   |   +-- __init__.py
|   |   |   |   +-- document_tools.py   # get_parsed_content, get_document_status, etc.
|   |   |   |   +-- category_tools.py   # get_categories, get_extraction_schema
|   |   |   |   +-- extraction_tools.py # get_extracted_values
|   |   |   |   +-- search_tools.py     # weaviate_hybrid_search
|   |   |   +-- schemas/                # Agent structured output schemas
|   |   |       +-- __init__.py
|   |   |       +-- classification.py   # ClassificationResult
|   |   |       +-- extraction.py       # ExtractionResult, ExtractedField
|   |   |       +-- judge.py            # JudgeResult, FieldEvaluation
|   |   |       +-- summary.py          # SummaryResult
|   |   |
|   |   +-- bulk/                       # Bulk processing pipeline
|   |   |   +-- __init__.py
|   |   |   +-- state_graph.py          # LangGraph StateGraph definition (7 nodes)
|   |   |   +-- state.py                # DocumentState TypedDict
|   |   |   +-- service.py              # BulkProcessingService (launch, track)
|   |   |   +-- nodes/                  # Individual pipeline nodes
|   |   |       +-- __init__.py
|   |   |       +-- parse_node.py
|   |   |       +-- classify_node.py
|   |   |       +-- extract_node.py
|   |   |       +-- judge_node.py
|   |   |       +-- summarize_node.py
|   |   |       +-- ingest_node.py
|   |   |       +-- finalize_node.py
|   |   |
|   |   +-- rag/                        # RAG ingestion and retrieval
|   |   |   +-- __init__.py
|   |   |   +-- weaviate_client.py      # Weaviate connection, collection setup
|   |   |   +-- chunker.py             # LangChain SemanticChunker wrapper
|   |   |   +-- ingestion.py            # Chunk + upsert to Weaviate
|   |   |   +-- search.py              # Hybrid search with filtering
|   |   |
|   |   +-- parser/                     # Document parsing
|   |   |   +-- __init__.py
|   |   |   +-- reducto.py             # Reducto Cloud API client
|   |   |
|   |   +-- storage/                    # File storage
|   |   |   +-- __init__.py
|   |   |   +-- local.py               # Local filesystem operations
|   |   |
|   |   +-- services/                   # Business logic services
|   |   |   +-- __init__.py
|   |   |   +-- document_service.py     # Upload, dedup, state machine
|   |   |   +-- parse_service.py        # Parse orchestration
|   |   |   +-- classify_service.py     # Classification orchestration
|   |   |   +-- extract_service.py      # Extraction + judge orchestration
|   |   |   +-- summarize_service.py    # Summarization orchestration
|   |   |   +-- ingest_service.py       # Ingestion orchestration
|   |   |   +-- state_machine.py        # Document state transition logic
|   |   |
|   |   +-- config/                     # Application configuration
|   |       +-- __init__.py
|   |       +-- settings.py             # Pydantic Settings (from .env + config.yml)
|   |
|   +-- alembic/                        # Database migrations
|   |   +-- env.py                      # Alembic environment config
|   |   +-- versions/                   # Migration files
|   |       +-- 001_initial_schema.py   # All 10 tables
|   |
|   +-- schemas/                        # Extraction YAML schemas (on disk)
|   |   +-- lpa.yml                     # Default LPA extraction fields
|   |
|   +-- tests/                          # Backend tests
|   |   +-- __init__.py
|   |   +-- conftest.py                 # Fixtures: test DB, test client
|   |   +-- test_documents.py
|   |   +-- test_parse.py
|   |   +-- test_classify.py
|   |   +-- test_extract.py
|   |   +-- test_summarize.py
|   |   +-- test_rag.py
|   |   +-- test_config.py
|   |   +-- test_bulk.py
|   |   +-- test_state_machine.py
|   |   +-- test_pii_filter.py
|   |
|   +-- config.yml                      # Application configuration (paths, chunking, bulk settings)
|   +-- .env.example                    # Environment variable template
|   +-- requirements.txt                # Python dependencies
|   +-- pyproject.toml                  # Project metadata and tool config
|   +-- alembic.ini                     # Alembic configuration
|
+-- frontend/                           # React SPA frontend
|   +-- src/                            # Application source code
|   |   +-- main.tsx                    # React entrypoint, providers
|   |   +-- App.tsx                     # Router setup, layout shell
|   |   |
|   |   +-- components/                 # UI components by domain
|   |   |   +-- documents/              # Document list, status badge
|   |   |   |   +-- DocumentList.tsx
|   |   |   |   +-- DocumentStatusBadge.tsx
|   |   |   |   +-- DocumentRow.tsx
|   |   |   +-- parse/                  # Parse and edit UI
|   |   |   |   +-- ParseView.tsx
|   |   |   |   +-- RichTextEditor.tsx
|   |   |   |   +-- SplitView.tsx
|   |   |   +-- classify/              # Classification UI
|   |   |   |   +-- ClassificationResult.tsx
|   |   |   |   +-- CategoryOverride.tsx
|   |   |   +-- extract/               # Extraction results UI
|   |   |   |   +-- ExtractionResultsTable.tsx
|   |   |   |   +-- ConfidenceBadge.tsx
|   |   |   |   +-- ConfidenceReviewPanel.tsx
|   |   |   |   +-- InlineFieldEditor.tsx
|   |   |   +-- summary/               # Summary display
|   |   |   |   +-- SummaryView.tsx
|   |   |   |   +-- KeyTopicTags.tsx
|   |   |   +-- chat/                  # RAG chat interface
|   |   |   |   +-- ChatInterface.tsx
|   |   |   |   +-- ChatMessage.tsx
|   |   |   |   +-- CitationCard.tsx
|   |   |   |   +-- ScopeSelector.tsx
|   |   |   |   +-- SearchModeToggle.tsx
|   |   |   +-- config/               # Config management
|   |   |   |   +-- CategoryManager.tsx
|   |   |   |   +-- CategoryFormModal.tsx
|   |   |   |   +-- ExtractionFieldEditor.tsx
|   |   |   |   +-- FieldFormModal.tsx
|   |   |   +-- bulk/                  # Bulk processing UI
|   |   |   |   +-- BulkJobDashboard.tsx
|   |   |   |   +-- BulkJobRow.tsx
|   |   |   |   +-- BulkProgressBar.tsx
|   |   |   |   +-- BulkUploadZone.tsx
|   |   |   +-- upload/               # Upload UI
|   |   |   |   +-- UploadDropzone.tsx
|   |   |   |   +-- UploadProgress.tsx
|   |   |   |   +-- FileTypeIcon.tsx
|   |   |   +-- ui/                    # Shared UI primitives
|   |   |       +-- Button.tsx
|   |   |       +-- Card.tsx
|   |   |       +-- Modal.tsx
|   |   |       +-- Badge.tsx
|   |   |       +-- Spinner.tsx
|   |   |       +-- EmptyState.tsx
|   |   |       +-- Layout.tsx
|   |   |       +-- Sidebar.tsx
|   |   |       +-- PageHeader.tsx
|   |   |
|   |   +-- pages/                     # Route-level page components
|   |   |   +-- DashboardPage.tsx       # / — document list
|   |   |   +-- UploadPage.tsx          # /upload
|   |   |   +-- ParsePage.tsx           # /documents/:id/parse
|   |   |   +-- ClassifyPage.tsx        # /documents/:id/classify
|   |   |   +-- ExtractPage.tsx         # /documents/:id/extract
|   |   |   +-- SummaryPage.tsx         # /documents/:id/summary
|   |   |   +-- ChatPage.tsx            # /documents/:id/chat
|   |   |   +-- CategoriesPage.tsx      # /config/categories
|   |   |   +-- ExtractionFieldsPage.tsx # /config/extraction-fields
|   |   |   +-- BulkPage.tsx            # /bulk
|   |   |
|   |   +-- hooks/                     # Custom React hooks
|   |   |   +-- useDocuments.ts         # TanStack Query hooks for documents
|   |   |   +-- useParse.ts            # Parse-related mutations/queries
|   |   |   +-- useClassify.ts         # Classification hooks
|   |   |   +-- useExtract.ts          # Extraction hooks
|   |   |   +-- useSummarize.ts        # Summary hooks
|   |   |   +-- useIngest.ts           # Ingestion hooks
|   |   |   +-- useRag.ts             # RAG query hooks
|   |   |   +-- useCategories.ts       # Category CRUD hooks
|   |   |   +-- useExtractionFields.ts # Extraction field hooks
|   |   |   +-- useBulk.ts            # Bulk job hooks with polling
|   |   |
|   |   +-- lib/                       # Utility libraries
|   |   |   +-- api/                   # API client layer
|   |   |   |   +-- client.ts          # Axios instance, interceptors, case transform
|   |   |   |   +-- documents.ts       # Document API functions
|   |   |   |   +-- parse.ts           # Parse API functions
|   |   |   |   +-- classify.ts        # Classify API functions
|   |   |   |   +-- extract.ts         # Extract API functions
|   |   |   |   +-- summarize.ts       # Summarize API functions
|   |   |   |   +-- ingest.ts          # Ingest API functions
|   |   |   |   +-- rag.ts            # RAG API functions
|   |   |   |   +-- config.ts         # Config API functions
|   |   |   |   +-- bulk.ts           # Bulk API functions
|   |   |   +-- config.ts             # App config constants
|   |   |   +-- utils.ts              # General utilities
|   |   |
|   |   +-- types/                     # TypeScript type definitions
|   |       +-- document.ts            # Document, DocumentStatus types
|   |       +-- parse.ts               # Parse response types
|   |       +-- classify.ts            # Classification types
|   |       +-- extract.ts             # Extraction, confidence types
|   |       +-- summary.ts             # Summary types
|   |       +-- rag.ts                # RAG query/response types
|   |       +-- config.ts             # Category, field types
|   |       +-- bulk.ts               # Bulk job types
|   |       +-- common.ts             # Shared types (ErrorResponse, etc.)
|   |
|   +-- public/                        # Static assets
|   +-- index.html                     # HTML entry point
|   +-- package.json                   # Node.js dependencies
|   +-- vite.config.ts                 # Vite configuration + proxy
|   +-- tailwind.config.ts             # Tailwind CSS 4 design tokens
|   +-- tsconfig.json                  # TypeScript configuration
|   +-- tsconfig.app.json             # App-specific TS config
|   +-- tsconfig.node.json            # Node-specific TS config
|
+-- docker-compose.yml                 # PostgreSQL 16 + Weaviate
+-- init.sh                            # Bootstrap script (create dirs, install deps, run migrations)
+-- .gitignore                         # Git ignore rules
+-- .env.example                       # Root-level env template
|
+-- data/                              # Local data storage (gitignored)
|   +-- upload/                        # Uploaded original files
|   +-- parsed/                        # Parsed markdown files
|   +-- schemas/                       # On-disk YAML schemas
|
+-- docs/                              # Project documentation
|   +-- superpowers/
|       +-- specs/                     # Design specifications
|
+-- specs/                             # Planning artifacts
    +-- brd/
    |   +-- brd.md                     # Business Requirements Document
    +-- stories/                       # User stories
    |   +-- E1-S1.md ... E9-S3.md     # 32 story files
    |   +-- dependency-graph.md        # Story dependency graph
    +-- design/                        # Architecture and design docs
        +-- system-design.md
        +-- api-contracts.md
        +-- api-contracts.schema.json
        +-- data-models.md
        +-- data-models.schema.json
        +-- folder-structure.md
        +-- component-map.md
        +-- deployment.md
```
