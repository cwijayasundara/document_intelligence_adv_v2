# Dependency Graph — PE Document Intelligence Platform

## Overview

- **9 Epics**, **32 Stories**, **6 Dependency Groups** (A–F)
- Groups execute in wave order: all stories within a group can run in parallel
- Each group depends only on prior groups being complete

---

## Group A — Foundation (no dependencies)

| Story ID | Title | Layer | Dependencies |
|----------|-------|-------|--------------|
| E1-S1 | Database types & ORM models | Types | — |
| E1-S2 | Application configuration | Config | — |
| E1-S3 | Database connection & migrations | Repository | — |
| E1-S4 | FastAPI application factory + health endpoint | API | — |

---

## Group B — Core Repositories & Agent Setup (depends on A)

| Story ID | Title | Layer | Dependencies |
|----------|-------|-------|--------------|
| E2-S1 | Document repository + upload service + API | Repository+Service+API | E1-S1, E1-S3, E1-S4 |
| E3-S1 | DeepAgent orchestrator scaffold | Service | E1-S2 |
| E3-S4 | Long-term memory (PostgreSQL-backed) | Repository+Service | E1-S1, E1-S3 |
| E4-S1 | Category & extraction schema CRUD | Repository+API | E1-S1, E1-S3, E1-S4 |
| E7-S1 | Frontend app shell, routing, API client | UI | — |

---

## Group C — Services, Agents & Frontend Core (depends on A+B)

| Story ID | Title | Layer | Dependencies |
|----------|-------|-------|--------------|
| E2-S2 | Document state machine | Service | E2-S1 |
| E2-S3 | Reducto parser + parse/edit API | Service+API | E2-S1 |
| E3-S2 | PII filtering middleware | Service | E3-S1 |
| E3-S3 | Short-term memory (session-based) | Service | E3-S1 |
| E4-S2 | Classifier subagent | Service | E3-S1, E3-S2, E4-S1 |
| E5-S1 | Extractor subagent (dynamic Pydantic models) | Service | E3-S1, E3-S2, E4-S1 |
| E5-S2 | Judge subagent (confidence scoring) | Service | E3-S1, E3-S2 |
| E6-S1 | Summarizer subagent + API | Service+API | E3-S1, E3-S2, E1-S4 |
| E6-S2 | Weaviate client + semantic chunking + ingestion | Service+API | E1-S2, E2-S1 |
| E7-S2 | Dashboard — document list with status | UI | E7-S1, E2-S1 |
| E7-S3 | Upload page with drag-drop | UI | E7-S1, E2-S1 |
| E8-S1 | Config management pages | UI | E7-S1, E4-S1 |

---

## Group D — AI APIs & Frontend Pages (depends on A+B+C)

| Story ID | Title | Layer | Dependencies |
|----------|-------|-------|--------------|
| E4-S3 | Classification API endpoint | API | E4-S2, E2-S2 |
| E5-S3 | Extraction API + results repository + review gate | Repository+API | E5-S1, E5-S2, E2-S2 |
| E6-S3 | RAG retriever subagent + query API | Service+API | E3-S1, E6-S2 |
| E7-S4 | Parse/edit page with TipTap split view | UI | E7-S1, E2-S3 |
| E8-S4 | Summary page with regenerate | UI | E7-S1, E6-S1 |
| E9-S1 | LangGraph bulk state graph | Service | E4-S2, E5-S1, E5-S2, E6-S1, E6-S2 |

---

## Group E — Frontend AI Pages & Bulk API (depends on A+B+C+D)

| Story ID | Title | Layer | Dependencies |
|----------|-------|-------|--------------|
| E8-S2 | Classification page with override | UI | E7-S1, E4-S3 |
| E8-S3 | Extraction results 3-column view + review gate | UI | E7-S1, E5-S3 |
| E8-S5 | RAG chat page with citations | UI | E7-S1, E6-S3 |
| E9-S2 | Bulk job repository + API | Repository+API | E9-S1, E1-S4 |

---

## Group F — Bulk UI (depends on A+B+C+D+E)

| Story ID | Title | Layer | Dependencies |
|----------|-------|-------|--------------|
| E9-S3 | Bulk upload + dashboard UI | UI | E9-S2, E7-S1 |

---

## Visual Dependency Flow

```
Group A ──► Group B ──► Group C ──► Group D ──► Group E ──► Group F
  E1          E2-S1      E2-S2      E4-S3      E8-S2      E9-S3
              E3-S1      E2-S3      E5-S3      E8-S3
              E3-S4      E3-S2      E6-S3      E8-S5
              E4-S1      E3-S3      E7-S4      E9-S2
              E7-S1      E4-S2      E8-S4
                         E5-S1      E9-S1
                         E5-S2
                         E6-S1
                         E6-S2
                         E7-S2
                         E7-S3
                         E8-S1
```

## Epic Summary

| Epic | Title | Stories | Groups |
|------|-------|---------|--------|
| E1 | Foundation Infrastructure | 4 | A |
| E2 | Document Upload & Parsing | 3 | B, C |
| E3 | Agent Framework & Memory | 4 | B, C |
| E4 | Classification & Config | 3 | B, C, D |
| E5 | Extraction & Judging | 3 | C, D |
| E6 | Summarization & RAG | 3 | C, D |
| E7 | Frontend Core | 4 | B, C, D |
| E8 | Frontend AI & Config | 5 | C, D, E |
| E9 | Bulk Processing | 3 | D, E, F |
