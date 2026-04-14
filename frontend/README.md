# PE Document Intelligence — Frontend

React + TypeScript frontend for the PE Document Intelligence platform. Built with Vite, Tailwind CSS v4, and React Router v7.

## Tech Stack

- **React 19** with TypeScript
- **Vite 6** — dev server, build, proxy
- **Tailwind CSS 4** — via `@tailwindcss/vite`
- **React Router 7** — client-side routing
- **TanStack React Query 5** — server state management with smart polling
- **Axios** — HTTP client
- **Recharts** — analytics charts
- **react-markdown** + remark-gfm + rehype — markdown rendering
- **react-dropzone** — file upload
- **Vitest** + Testing Library — unit tests

## Getting Started

```bash
npm install
npm run dev        # http://localhost:5173
```

The dev server proxies `/api` requests to `http://localhost:8000` (the FastAPI backend).

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | Backend API base URL |

## Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start Vite dev server on port 5173 |
| `npm run build` | Type-check and build for production |
| `npm run preview` | Preview production build locally |
| `npm run lint` | Run ESLint |
| `npm test` | Run Vitest |

## Key Features

### Unified Pipeline Workflow
Every document (single or bulk upload) flows through the same LangGraph pipeline. The **PipelineStepper** component shows real-time per-node progress:

- ✅ **Completed** nodes (green check)
- 🔄 **Running** nodes (blue spinner)
- ❌ **Failed** nodes (red X with Retry button)
- ⏸️ **Awaiting review** nodes (amber pause with Review button)
- ⚪ **Not started** nodes (gray circle)

### Human-in-the-Loop Review
When a document has low parse confidence (<90%) or low-confidence extractions, the pipeline pauses and the user is routed to an inline review UI:
- **Parse review** — edit the parsed markdown content; pipeline auto-resumes on save
- **Extraction review** — mark flagged fields as reviewed; pipeline auto-resumes when all are approved

### Bulk Processing with Mixed States
A bulk upload of 10 documents may have some auto-complete and others pause for review. The bulk job detail shows per-document status; clicking "Review" on a paused doc takes the user to its workflow page.

### Agentic RAG Chat
The chat page uses agentic RAG — the LLM can search documents, look up extraction results, or retrieve summaries via tools, reformulating queries as needed.

## Project Structure

```
src/
  App.tsx                          # Route definitions
  main.tsx                         # Entry point (React Router, React Query providers)
  index.css                        # Tailwind imports

  pages/
    DashboardPage.tsx              # Landing page with document list + pipeline steppers
    UploadPage.tsx                 # Drag-and-drop document upload
    ParsePage.tsx                  # Parsed content editor
    ClassifyPage.tsx               # Classification results
    ExtractionPage.tsx             # Extraction table with review gate
    SummaryPage.tsx                # AI-generated summary
    ChatPage.tsx                   # Agentic RAG chat
    BulkPage.tsx                   # Bulk job list with per-doc status
    CategoriesPage.tsx             # Category config
    ExtractionFieldsPage.tsx       # Extraction field config
    InsightsPage.tsx               # Cross-document insights
    AnalyticsPage.tsx              # Usage analytics

  components/
    ui/                            # Layout primitives (Layout, Sidebar, PageHeader, EmptyState)
    documents/
      DocumentList.tsx             # Tabular document list
      DocumentRow.tsx              # Single row with actions
      DocumentCardGrid.tsx         # Card view
      DocumentDetailPanel.tsx      # Side panel with details
      DocumentTreePanel.tsx        # Hierarchical tree view
      DocumentStatusBadge.tsx      # Status badge (incl. new pipeline statuses)
      PipelineStepper.tsx          # Horizontal pipeline progress stepper
    bulk/                          # Bulk job list + detail
    chat/                          # RAG chat interface
    classify/                      # Classification display
    config/                        # Category + field config UIs
    extraction/                    # Extraction table with review gate
    parse/                         # Parse editor with confidence banner
    summary/                       # Summary display
    upload/                        # Dropzone + upload progress
    analytics/                     # Charts & widgets

  hooks/
    usePipeline.ts                 # Pipeline status + start/resume/retry actions
    useDocuments.ts                # Document CRUD
    useUpload.ts                   # File upload with progress
    useParse.ts                    # Parse operations
    useClassify.ts                 # Classification operations
    useExtraction.ts               # Extraction operations
    useSummary.ts                  # Summary operations
    useRagChat.ts                  # RAG chat messaging
    useBulk.ts                     # Bulk processing
    useCategories.ts               # Category config
    useExtractionFields.ts         # Extraction field config
    useAudit.ts                    # Audit log
    useSession.ts                  # Session management
    useEventStream.ts              # SSE event stream listener

  lib/
    config.ts                      # App constants (API base URL, app name)
    api/
      client.ts                    # Axios instance
      pipeline.ts                  # Pipeline endpoints (start, resume, retry, status)
      documents.ts                 # Document endpoints
      parse.ts                     # Parse endpoints
      classify.ts                  # Classify endpoints
      extraction.ts                # Extraction endpoints
      summary.ts                   # Summary endpoints
      rag.ts                       # RAG chat endpoints
      bulk.ts                      # Bulk processing endpoints
      config.ts                    # Config endpoints
      analytics.ts                 # Analytics endpoints
      audit.ts                     # Audit endpoints

  types/
    pipeline.ts                    # PipelineNodeName, NodeStatus, PipelineStatus
    common.ts                      # Shared types (DocumentStatus union)
    document.ts                    # Document types
    parse.ts
    classify.ts
    extraction.ts
    summary.ts
    rag.ts
    bulk.ts
    config.ts
    analytics.ts
    audit.ts
```

## Routes

| Path | Page | Description |
|---|---|---|
| `/` | Dashboard | Document list with pipeline steppers |
| `/upload` | Upload | Drag-and-drop upload (auto-starts pipeline) |
| `/documents/:id/parse` | Parse | View and edit parsed content |
| `/documents/:id/classify` | Classify | Document classification results |
| `/documents/:id/extract` | Extract | Review extracted fields |
| `/documents/:id/summary` | Summary | AI-generated summary |
| `/documents/:id/chat` | Chat | Agentic RAG Q&A |
| `/config/categories` | Categories | Manage classification categories |
| `/config/extraction-fields` | Fields | Manage extraction field definitions |
| `/bulk` | Bulk | Batch process multiple documents |
| `/insights` | Insights | Cross-document analysis |
| `/analytics` | Analytics | Usage metrics and charts |

## Pipeline Integration

### `usePipeline` Hooks

```typescript
// Poll pipeline status every 3s while "running"
const { data: status } = usePipelineStatus(docId);

// Start pipeline for a document
const { startPipeline } = useStartPipeline();

// Resume after human review (edit/approval)
const { resumePipeline } = useResumePipeline();

// Retry a failed node
const { retryNode } = useRetryNode();
```

### `PipelineStepper` Component

```tsx
<PipelineStepper
  nodeStatuses={doc.pipelineNodeStatus}
  onRetry={(node) => retryNode(docId, node)}
  onReview={(node) => navigate(`/documents/${docId}/${node}`)}
/>

// Compact mode for table rows
<PipelineStepper nodeStatuses={doc.pipelineNodeStatus} compact />
```

### New Document Statuses

The `DocumentStatusBadge` supports the pipeline-specific statuses:
- `processing` — pipeline is running (blue)
- `awaiting_parse_review` — paused for user to edit parsed content (amber)
- `awaiting_extraction_review` — paused for user to approve extractions (amber)

## Build Output

```bash
npm run build
# Type-checks with TypeScript, then builds to dist/
```

Production builds are fully static and can be served from any CDN. Configure `VITE_API_BASE_URL` at build time for the deployed backend URL.
