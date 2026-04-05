# PE Document Intelligence — Frontend

React + TypeScript frontend for the PE Document Intelligence platform. Built with Vite, Tailwind CSS v4, and React Router v7.

## Tech Stack

- **React 19** with TypeScript
- **Vite 6** (dev server, build, proxy)
- **Tailwind CSS 4** (via `@tailwindcss/vite`)
- **React Router 7** — client-side routing
- **TanStack React Query 5** — server state management
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

## Project Structure

```
src/
  App.tsx                  # Route definitions
  main.tsx                 # Entry point (React Router, React Query providers)
  index.css                # Tailwind imports

  pages/                   # Route-level page components
    DashboardPage.tsx      # Landing page (/)
    UploadPage.tsx         # Document upload (/upload)
    ParsePage.tsx          # Parse results (/documents/:id/parse)
    ClassifyPage.tsx       # Classification (/documents/:id/classify)
    ExtractionPage.tsx     # Field extraction (/documents/:id/extract)
    SummaryPage.tsx        # Summary (/documents/:id/summary)
    ChatPage.tsx           # RAG chat (/documents/:id/chat)
    CategoriesPage.tsx     # Category config (/config/categories)
    ExtractionFieldsPage.tsx # Extraction field config (/config/extraction-fields)
    BulkPage.tsx           # Bulk processing (/bulk)
    InsightsPage.tsx       # Cross-document insights (/insights)
    AnalyticsPage.tsx      # Usage analytics (/analytics)

  components/
    ui/                    # Shared layout & UI primitives
      Layout.tsx           # App shell with sidebar
      Sidebar.tsx          # Navigation sidebar
      PageHeader.tsx       # Page title header
      EmptyState.tsx       # Empty state placeholder
    analytics/             # Analytics charts & widgets
    bulk/                  # Bulk processing components
    chat/                  # RAG chat interface
    classify/              # Classification display
    config/                # Config management (categories, fields)
    documents/             # Document list & detail
    extraction/            # Extraction results display
    parse/                 # Parse results display
    summary/               # Summary display
    upload/                # Upload dropzone & progress

  hooks/                   # Custom React hooks
    useDocuments.ts        # Document CRUD
    useUpload.ts           # File upload with progress
    useParse.ts            # Parse operations
    useClassify.ts         # Classification operations
    useExtraction.ts       # Extraction operations
    useExtractionFields.ts # Extraction field config
    useSummary.ts          # Summary operations
    useRagChat.ts          # RAG chat messaging
    useBulk.ts             # Bulk processing
    useCategories.ts       # Category config
    useAudit.ts            # Audit log
    useSession.ts          # Session management
    useEventStream.ts      # SSE event stream listener

  lib/
    config.ts              # App constants (API base URL, app name)
    api/                   # API client modules
      client.ts            # Axios instance
      documents.ts         # Document endpoints
      parse.ts             # Parse endpoints
      classify.ts          # Classify endpoints
      extraction.ts        # Extraction endpoints
      summary.ts           # Summary endpoints
      rag.ts               # RAG chat endpoints
      bulk.ts              # Bulk processing endpoints
      config.ts            # Config endpoints
      analytics.ts         # Analytics endpoints
      audit.ts             # Audit endpoints

  types/                   # TypeScript type definitions
    common.ts              # Shared types
    document.ts            # Document types
    parse.ts               # Parse types
    classify.ts            # Classify types
    extraction.ts          # Extraction types
    summary.ts             # Summary types
    rag.ts                 # RAG chat types
    bulk.ts                # Bulk types
    config.ts              # Config types
    analytics.ts           # Analytics types
    audit.ts               # Audit types
```

## Routes

| Path | Page | Description |
|---|---|---|
| `/` | Dashboard | Document list and quick actions |
| `/upload` | Upload | Drag-and-drop document upload |
| `/documents/:id/parse` | Parse | Parsed document content |
| `/documents/:id/classify` | Classify | Document classification results |
| `/documents/:id/extract` | Extract | Extracted field values |
| `/documents/:id/summary` | Summary | AI-generated summary |
| `/documents/:id/chat` | Chat | RAG-powered Q&A over the document |
| `/config/categories` | Categories | Manage classification categories |
| `/config/extraction-fields` | Fields | Manage extraction field definitions |
| `/bulk` | Bulk | Batch process multiple documents |
| `/insights` | Insights | Cross-document analysis |
| `/analytics` | Analytics | Usage metrics and charts |
