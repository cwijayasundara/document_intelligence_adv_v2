# PE Document Intelligence — Evaluation Framework

A production-grade eval framework that grades every LLM touchpoint of the
platform: the **LangGraph bulk pipeline**, the **RAG (basic + agentic) layer**,
and the **text-to-SQL data agent**. Results are persisted to PostgreSQL and
optionally streamed to LangSmith, then surfaced through a `/evals` dashboard
for trend tracking and per-run drill-down.

---

## 1. What we evaluate, and why

The platform has eight LLM-shaped surfaces. Each one needs its own scoring
contract because what counts as "correct" differs by stage.

| Stage          | Production code under test                              | Why it needs evals                                           |
| -------------- | ------------------------------------------------------- | ------------------------------------------------------------ |
| classification | `src/graph_nodes/classifier.classify_document`          | Wrong category sends a doc through the wrong extraction schema. |
| extraction     | `src/graph_nodes/extractor.extract_fields`              | Field accuracy + verbatim source provenance.                 |
| judge (meta)   | `src/graph_nodes/judge` confidence verdicts             | Confidence must correlate with correctness or it's useless.  |
| summarize      | `src/graph_nodes/summarizer.summarize_document`         | Faithfulness + PE-checklist coverage.                        |
| rag            | `src/services/rag_service.RAGService.query`             | Retrieval quality + answer faithfulness.                     |
| agentic_rag    | `src/rag/agent.agentic_rag_query` (LangGraph ReAct)     | Tool-call **trajectory** quality, not just final answer.     |
| sql            | `src/data_agent.agent.run_analytics_query`              | NL→SQL safety + intent + chart shape.                        |
| pipeline       | `src/bulk/pipeline.build_pipeline` (full LangGraph DAG) | Stage reachability + review-gate firing.                     |

**Design principle.** Every evaluator returns the same shape:
`{"key": str, "score": float | None, "comment": str}`. That uniformity is what
lets the runner aggregate, persist, and chart anything without per-stage glue.

---

## 2. Evaluator taxonomy (four layers)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  metric-based      │  llm-as-judge      │  rubric-based  │  trajectory   │
│  (deterministic)   │  (single criterion)│  (multi-crit)  │  (tool-calls) │
├──────────────────────────────────────────────────────────────────────────┤
│  exact match       │  faithfulness      │  YAML rubric   │  subset       │
│  numeric tolerance │  answer-relevance  │  weighted mean │  partial-order│
│  Recall@K, MRR     │  context-relevance │  per-criterion │  call budget  │
│  nDCG@K            │  RAGAS triad       │  reasoning     │  arg quality  │
│  ECE (calibration) │  judge-meta calib  │                │               │
│  source substring  │  SQL intent match  │                │               │
│  PE-checklist cov  │                    │                │               │
└──────────────────────────────────────────────────────────────────────────┘
   cheap, repro      slower, $$$           medium $$$        cheap+LLM
```

### 2.1 Metric-based (deterministic)

Files: `backend/evals/evaluators/metric_based/`. No LLM call — these are pure
Python and run in CI with no API keys. Used for fast pre-merge checks.

- `classification_accuracy` — case-insensitive name match against
  `expected_category`.
- `classification_confidence_in_range` — `expected_min_confidence` /
  `expected_max_confidence` window.
- `calibration_ece` — **Expected Calibration Error** across the whole run.
  Buckets predicted confidence into deciles; ECE is the weighted sum of
  `|mean_confidence - accuracy|` per bucket. This is the canonical
  "is the model's confidence honest" metric. Lower is better.
- `extraction_exact_match` — whitespace/loose-punctuation normalised match,
  honouring `expected_accepted_values` and `expected_empty=True`.
- `extraction_numeric_tolerance` — absolute-tolerance numeric compare for
  fees, rates, periods; handles `%`, `$`, `,` formatting.
- `extraction_source_substring` — verifies predicted `source_text` is a
  case-insensitive substring of the source document (and contains
  `expected_source_substring` when supplied). Catches hallucinated provenance.
- `retrieval_recall_at_k`, `retrieval_mrr`, `retrieval_ndcg_at_k` —
  standard IR metrics over `expected_relevant_chunk_substrings`.
- `rag_answer_contains` (`all_of` / `any_of` modes), `rag_citation_count_in_range`.
- `summary_pe_checklist_coverage`, `summary_topic_count`.

### 2.2 LLM-as-judge (single criterion)

Files: `backend/evals/evaluators/llm_judge/`. Each judge is a small focused
prompt with **structured output via Pydantic** (`BinaryJudgement`,
`FaithfulnessJudgement`, `AnswerRelevanceJudgement`, `JudgeMetaJudgement`).
The judge model is auto-upgraded to one tier above production (configurable
via `EVAL_JUDGE_MODEL`).

- `summary_faithfulness`, `rag_answer_faithfulness` — strict claim-by-claim
  grounding check. Returns `unsupported_claims` for auditing.
- `rag_answer_relevance`, `rag_context_relevance` — does the answer address
  the question; how relevant is each retrieved chunk.
- `extraction_source_fidelity` — three-way check: substring in doc, value
  supported by source_text, source_text is the **best** supporting passage.
- `judge_meta_calibration` — grades the **production judge node** against
  the gold answer. Catches over-confident wrong predictions and under-confident
  right ones.
- `sql_intent_match` — would the SQL, if executed, actually answer the user's
  question as a PE analyst would interpret it.
- `ragas_triad` — optional wrapper around RAGAS faithfulness +
  answer-relevancy + context-precision; gracefully degrades to `score=None`
  when RAGAS is not installed.

### 2.3 Rubric-based (multi-criterion)

File: `backend/evals/evaluators/rubric.py`. YAML rubrics under
`backend/evals/rubrics/` define criteria with `weight`, `description`,
optional `anchors` (1..5 score guidance) and `scoring` text. The runner asks
the judge to score each criterion in one structured call, then computes a
weighted composite normalised to `[0, 1]` and a `raw_score` on the rubric's
scale.

Shipped rubrics:

| Rubric             | Criteria                                                                                                 | Weight sum |
| ------------------ | -------------------------------------------------------------------------------------------------------- | ---------- |
| `extraction`       | verbatim_quote (0.35), value_format (0.25), unit_correctness (0.20), completeness (0.20)                 | 1.00       |
| `summary`          | pe_attribute_coverage (0.35), faithfulness (0.35), non_redundancy (0.10), fluency_and_length (0.10), topic_tags_relevance (0.10) | 1.00 |
| `sql`              | sql_intent_match (0.35), sql_parsimony (0.15), chart_type_appropriate (0.20), chart_axes_sensible (0.20), explanation_quality (0.10) | 1.00 |
| `agent_trajectory` | tool_selection (0.30), query_reformulation_quality (0.25), hops_efficient (0.20), final_answer_grounded (0.25) | 1.00 |

`make_rubric_evaluator(rubric_name, context_keys=[…])` builds a LangSmith-
style `(run, example) -> dict` callable so a rubric drops into any runner's
evaluator list with no special handling.

### 2.4 Trajectory (agentic RAG)

File: `backend/evals/evaluators/trajectory.py`. Grades the **sequence of
tool calls** the ReAct agent made — independent of whether the final answer
was correct. A correct answer reached via 12 redundant tool calls is a worse
agent than one that got there in two.

- `trajectory_subset` — required tools ⊆ called tools (`expected_tools`).
- `trajectory_order` — `expected_tool_order=[[A, B], …]` partial-order
  pairs. Each pair `[A, B]` asserts "if both are called, A precedes B".
- `no_unnecessary_calls` — linear penalty beyond `expected_max_calls`
  (`1.0` at budget, `0.5` at 2× budget, `0.0` at 3×).
- `tool_input_quality` — LLM-judge: did the agent's reformulated tool args
  improve over the raw user query?
- `rubric_agent_trajectory` — full multi-criterion rubric (above).

### 2.5 SQL safety + execution-match

File: `backend/evals/evaluators/sql.py`. Uses `sqlglot` to parse and walk
the AST so safety checks are AST-based, not regex.

- `sql_validity` — single, parseable Postgres statement.
- `sql_safety` — rejects DDL/DML (`Insert`, `Update`, `Delete`, `Drop`,
  `Create`, `Alter`, `Truncate`, `Merge`, `Grant`, `Revoke`). Only SELECT
  (or `WITH … SELECT`) passes.
- `sql_rejected_as_expected` — for negative examples
  (`expected_sql_rejected=True`), confirms the agent **refused** (empty SQL
  + non-empty error/explanation) rather than producing unsafe SQL. Also
  validates `expected_error_contains` tokens.
- `sql_contains_keywords` — soft signal that required keywords appear.
- `chart_shape` — chart_type in `expected_accepted_chart_types`.
- `make_sql_exec_match(session_factory)` — **executes both reference and
  predicted SQL inside a rolled-back transaction**, then compares row-sets
  for set-equality (Jaccard fallback for partial matches). The rollback
  guarantees read-only semantics regardless of what the agent generated.

---

## 3. Datasets

### 3.1 Layout

```
backend/evals/datasets/
├── classification_golden.jsonl      # 10 examples (target 50–100)
├── extraction_golden.jsonl          # 15 examples (target 30–50)
├── summary_golden.jsonl             #  3 examples (target 30)
├── rag_golden.jsonl                 # 10 examples (target 100)
├── sql_golden.jsonl                 #  9 examples (target 60)
├── pipeline_golden.jsonl            #  3 examples (target 10)
├── regression_corrections.jsonl     # auto-harvested from user corrections
└── adversarial_synthetic.jsonl      # synthesised perturbations (planned)
```

### 3.2 Record shape

One JSONL line per golden example. Common envelope:

```jsonc
{
  "id": "ext_lpa_horizon_management_fee",
  "tags": ["positive", "numeric"],
  "notes": "Optional human comment.",

  // Inputs (anything not prefixed expected_/reference_/pe_checklist):
  "doc_id": "lpa_horizon",
  "parsed_path": "data/parsed/LPA_Horizon_Equity_Partners_IV.md",
  "field_name": "management_fee_rate",
  "data_type": "percentage",

  // Outputs (graded against):
  "expected_value": "2.0%",
  "expected_numeric_value": 2.0,
  "expected_tolerance": 0.05,
  "expected_source_substring": "2.0%"
}
```

The runner's `_split_inputs_outputs` heuristic routes anything starting with
`expected_` / `reference_` (plus `pe_checklist`) to the `outputs` dict,
everything else to `inputs`, and the envelope keys `id`/`tags`/`notes`/
`source` to metadata.

### 3.3 Regression harvesting (closed loop)

`backend/evals/regression_harvest.py` — every time a user corrects a
classification or extraction in the UI, the correction lands in LangGraph's
long-term memory under `classification_corrections` /
`extraction_corrections`. The harvest job materialises those into
`regression_corrections.jsonl` so the next eval run replays them as a
regression test. **New corrections become new regressions automatically** —
the dogfood loop closes itself.

### 3.4 LangSmith sync

`backend/evals/dataset_sync.py` mirrors local JSONL into LangSmith datasets
named `pe-doc-intel/<stage>`. The sync is idempotent: examples are matched
on `metadata.ref_id` (the local `id`), then created / updated / left alone.
Counts are returned in a `SyncResult` dataclass for CLI reporting.

---

## 4. Runners

Files: `backend/evals/runners/`. Every stage's runner provides:

1. An async `predict(example)` that calls the **production LLM touchpoint**
   (no shadow re-implementations) and returns a dict shaped like the
   evaluator input.
2. A list of `(evaluator_key, evaluator_callable)` typically composed from
   `metric_based.ALL_EVALUATORS` + `llm_judge` modules + a rubric.

`backend/evals/runners/_base.py:run_experiment()` does the heavy lifting:

```
load JSONL → for each example
                ├── call predict(ex)        # production LLM call
                ├── for each evaluator
                │       ├── invoke (sync or async, both supported)
                │       ├── persist EvalResult row
                │       └── accumulate score
                └── persist progress
finalise EvalRun row → return summary { run_id, summary_scores, per_example }
```

Notes on `_base.py`:

- **Persistence is best-effort** — if the DB connection fails (CI without
  Postgres, etc.) we log a warning and continue with in-memory results.
- **Evaluator failures are isolated** — one evaluator raising never kills
  the whole run; the failure is recorded with `score=None` and a `comment`.
- **Predict failures are recorded** — the error becomes the prediction's
  `error` field and evaluators score against it (most return `0.0`).
- **Git SHA + model name + judge model + tags** are all stamped on the
  `EvalRun` row so trends are honest.

### Stage-by-stage runners

| Runner                  | Production call                          | Evaluators wired in                                                                                  |
| ----------------------- | ---------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `run_classification.py` | `classify_document()`                    | accuracy, confidence-in-range                                                                        |
| `run_extraction.py`     | `extract_fields()`                       | exact_match, numeric_tolerance, source_substring, **+ extraction_source_fidelity** (judge)           |
| `run_summary.py`        | `summarize_document()`                   | pe_checklist_coverage, topic_count, **+ summary_faithfulness + rubric_summary**                      |
| `run_rag.py`            | `RAGService.query()`                     | recall@5, MRR, nDCG@10, answer_contains, citation_count, **+ faithfulness/relevance/RAGAS triad**    |
| `run_agentic_rag.py`    | LangGraph ReAct (`agentic_rag_query`)    | trajectory_subset/order, no_unnecessary_calls, **+ tool_input_quality + rubric_agent_trajectory**    |
| `run_sql.py`            | `run_analytics_query()` (data agent)     | sql_validity, sql_safety, sql_rejected_as_expected, sql_contains_keywords, chart_shape, **+ sql_intent_match + rubric_sql** |
| `run_pipeline.py`       | `build_pipeline().ainvoke(payload)`      | pipeline_stages_subset, pipeline_gate_correctness                                                    |

LLM-using evaluators are conditionally wired only when `OPENAI_API_KEY` is
set — so the same code path runs both in CI (deterministic-only) and
locally (full suite).

---

## 5. Persistence & API

### 5.1 Schema (Alembic 004)

`backend/alembic/versions/004_add_eval_runs.py` introduces two tables:

```
eval_runs
  id (uuid pk)
  stage                  classification | extraction | summary | rag | sql | agentic_rag | pipeline
  dataset_name           pe-doc-intel/<stage>
  dataset_version        optional (e.g. langsmith dataset commit)
  model                  production model used for the run
  judge_model            judge model used (one tier above prod by default)
  git_sha                code SHA at run time
  total_examples
  duration_seconds
  langsmith_experiment_url
  status                 running | completed | failed
  error_message
  summary_scores         JSONB { evaluator_key: float }
  tags                   JSONB list
  created_at, updated_at
  INDEX(stage, created_at)

eval_results
  id (uuid pk)
  run_id                 FK eval_runs(id) ON DELETE CASCADE
  example_id             string ref into the JSONL
  evaluator_key          e.g. "extraction_exact_match"
  score                  float | NULL (NULL = n/a or evaluator error)
  passed                 bool | NULL
  comment                text
  prediction             JSONB
  expected               JSONB
  criteria_breakdown     JSONB (rubric per-criterion scores)
  INDEX(run_id, evaluator_key)
```

### 5.2 Repository

`backend/src/db/repositories/evals_repo.py:EvalRunRepository`:

- `create_run(...)` / `add_result(...)` / `finalise_run(...)` — write path
  used by the runner.
- `list_runs(stage?, limit, offset)` — paginated listing.
- `get_run(id)` / `get_results(id, evaluator_key?)` — drill-down.
- `latest_run_per_stage()` — one row per stage, the latest **completed** run
  (used by the overview scorecards).
- `trend(stage, evaluator_key, limit)` — time-series of one metric across
  runs (used by the trends page).

### 5.3 HTTP API

`backend/src/api/routers/evals.py` — registered as `/api/v1/evals/*`:

| Method | Path                       | Purpose                                                |
| ------ | -------------------------- | ------------------------------------------------------ |
| GET    | `/evals/overview`          | Scorecards per stage (last run + delta vs. previous)   |
| GET    | `/evals/runs`              | Paginated runs (filter by `stage`)                     |
| GET    | `/evals/runs/{id}`         | One run + all per-result rows                          |
| POST   | `/evals/runs`              | Trigger a run (stage, subset?, tags?, model?) — 202    |
| GET    | `/evals/trends`            | Time-series for `(stage, evaluator_key)`               |

The `_PRIMARY_METRIC` map in the router decides which evaluator is the
"headline" score for each stage — that's what the scorecards show:

```python
classification → classification_accuracy
extraction     → extraction_exact_match
summary        → summary_pe_checklist_coverage
rag            → rag_answer_contains
sql            → sql_validity
agentic_rag    → trajectory_subset
pipeline       → pipeline_stages_subset
```

### 5.4 Frontend

- `frontend/src/lib/api/evals.ts` — Axios client (`fetchOverview`,
  `fetchRuns`, `fetchRun`, `triggerRun`, `fetchTrend`).
- `frontend/src/hooks/useEvals.ts` — TanStack Query hooks.
- `frontend/src/types/evals.ts` — TS types mirroring the Python schemas.
- `frontend/src/components/evals/`
  - `ScoreCard.tsx` — primary metric, delta arrow, run-now button.
  - `MetricBreakdown.tsx` — all evaluator scores for one run.
  - `ResultsTable.tsx` — per-example × per-evaluator drill-down.
  - `TrajectoryViewer.tsx` — agentic-RAG tool-call timeline.
- Pages (sidebar entries: "Evals", "Eval Trends"):
  - `/evals` → `EvalsPage` — overview grid of scorecards.
  - `/evals/trends` → `EvalTrendsPage` — pick stage + evaluator, get a chart.
  - `/evals/runs/:id` → `EvalRunDetailPage` — full run breakdown.

---

## 6. CLI

`python -m backend.evals.cli`:

```bash
# What stages exist + how many golden examples each has.
uv run python -m backend.evals.cli list-stages

# Push every non-empty JSONL into LangSmith as pe-doc-intel/<stage>.
uv run python -m backend.evals.cli sync-datasets

# Pull user corrections from long-term memory into regression_corrections.jsonl.
uv run python -m backend.evals.cli harvest-regressions

# Run one stage, optionally on the first N examples.
uv run python -m backend.evals.cli run --stage extraction --subset 5

# Run one stage filtered by tags.
uv run python -m backend.evals.cli run --stage rag --tags single_hop numeric

# Run everything.
uv run python -m backend.evals.cli run --stage all
```

Exit code is non-zero if any stage failed, so the CLI is CI-friendly.

---

## 7. Tests for the framework itself (meta-tests)

The framework has its own pytest suite — evaluators must be reliable before
they grade anything else. Files under `backend/tests/evals/`:

| Test file                         | Coverage                                                                                  |
| --------------------------------- | ----------------------------------------------------------------------------------------- |
| `test_evaluators_metric_based.py` | Every deterministic metric: classification, ECE, extraction (exact/numeric/source), retrieval (recall/MRR/nDCG), RAG answer/citations, summary checklist/topics. |
| `test_evaluators_sql.py`          | sqlglot-based parse/safety/refusal checks; chart shape; keyword containment.              |
| `test_evaluators_trajectory.py`   | subset, partial-order, call budget; LangChain message → tool_call extraction.             |
| `test_rubric_aggregate.py`        | Rubric weighted aggregation, score clipping, missing-criterion floor, YAML loading.       |

These tests use **duck-typed `_FakeRun` / `_FakeExample` dataclasses** so they
run in CI without the LangSmith SDK or any LLM key. Coverage of the
evaluator code is comprehensive (>90% line for the metric / sql / rubric /
trajectory modules).

In addition, the existing `backend/tests/evals/test_pipeline.py`,
`test_classification.py`, `test_extraction.py`, `test_rag.py`,
`test_summarization.py`, `test_analytics.py` continue to provide
**integration-level** smoke coverage of the production code paths the
runners exercise.

---

## 8. Observability

- **LangSmith** — when `LANGSMITH_API_KEY` and
  `LANGCHAIN_TRACING_V2=true` are set, every predict/evaluator call lands
  in the `pe-doc-intel-evals` project. Run rows store the experiment URL
  in `langsmith_experiment_url`.
- **Arize Phoenix (optional)** — set
  `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:6006/v1/traces` and the
  backend OTel tracer (`src/observability/tracing.py`) ships spans to a
  local Phoenix container for live debugging.
- **Postgres** — `eval_runs` + `eval_results` tables are the source of
  truth. The dashboard queries them; LangSmith is the secondary trace store.

---

## 9. Environment

Required:

- `OPENAI_API_KEY` — production model.
- `DATABASE_URL` — for run persistence.
- `LANGSMITH_API_KEY` — for `sync-datasets` and trace upload.

Recommended:

- `LANGCHAIN_TRACING_V2=true`
- `LANGCHAIN_PROJECT=pe-doc-intel-evals`
- `EVAL_JUDGE_MODEL` — override the judge model (defaults: `gpt-5.2 →
  gpt-5.3`, `gpt-5.1 → gpt-5.2`).
- `OTEL_EXPORTER_OTLP_ENDPOINT` — Phoenix.

---

## 10. End-to-end example

```bash
# 1. Bring up infra and migrate.
docker compose up -d postgres weaviate
cd backend && uv sync && uv run alembic upgrade head

# 2. Sync local goldens to LangSmith (idempotent).
uv run python -m backend.evals.cli sync-datasets

# 3. Smoke-run extraction on 5 examples.
uv run python -m backend.evals.cli run --stage extraction --subset 5
# → [run] stage=extraction result={"run_id":"…","summary_scores":{
#       "extraction_exact_match":0.8,
#       "extraction_numeric_tolerance":1.0,
#       "extraction_source_substring":0.8,
#       "extraction_source_fidelity":0.92,
#       "rubric_extraction":0.86 }}

# 4. Open the dashboard.
cd ../frontend && npm run dev
# → http://localhost:5173/evals
#   Click a scorecard → /evals/runs/<id> for per-example drill-down.
#   Click "Eval Trends" → pick (stage, evaluator) for the time-series chart.

# 5. As users correct results in the UI, harvest them into a regression set:
uv run python -m backend.evals.cli harvest-regressions
# → Wrote 24 regression records to backend/evals/datasets/regression_corrections.jsonl
```

---

## 11. Extending the framework

**Add a new evaluator (deterministic)**:

1. Drop a function in
   `backend/evals/evaluators/metric_based/<concern>.py` returning
   `{"key", "score", "comment"}`.
2. Re-export it from `metric_based/__init__.py:ALL_EVALUATORS`.
3. Add a unit test in `backend/tests/evals/test_evaluators_metric_based.py`
   using `_FakeRun` / `_FakeExample`.
4. Wire it into the relevant runner's `_evaluators()` list.

**Add a new rubric**:

1. Write `backend/evals/rubrics/<name>.yaml` with `criteria` (`id`,
   `weight`, `description`, optional `anchors`).
2. Wire it via
   `make_rubric_evaluator("<name>", context_keys=[...])` in the runner.

**Add a new stage**:

1. Create `backend/evals/runners/run_<stage>.py` with `_predict()`,
   `_evaluators()`, and the `run_experiment` alias.
2. Append the stage to `STAGE_CHOICES` in `backend/evals/cli.py` and
   `backend/src/api/routers/evals.py`.
3. Add a JSONL under `backend/evals/datasets/<stage>_golden.jsonl`.
4. Register a primary metric in `_PRIMARY_METRIC` so it shows on the
   overview page.

---

## 12. Files in this change

```
backend/
├── alembic/versions/
│   └── 004_add_eval_runs.py                    # eval_runs + eval_results tables
├── evals/
│   ├── README.md
│   ├── cli.py                                  # list-stages | sync-datasets | run | harvest-regressions
│   ├── dataset_sync.py                         # JSONL ↔ LangSmith
│   ├── regression_harvest.py                   # corrections memory → regression JSONL
│   ├── datasets/                               # 6 stage golden JSONLs
│   ├── rubrics/                                # 4 YAML rubrics
│   ├── evaluators/
│   │   ├── metric_based/                       # 6 modules + ALL_EVALUATORS map
│   │   ├── llm_judge/                          # 7 modules incl. _base, ragas, judge_meta
│   │   ├── rubric.py                           # YAML rubric runner + factory
│   │   ├── sql.py                              # validity, safety, refusal, exec-match
│   │   └── trajectory.py                       # subset, order, budget, arg-quality
│   └── runners/
│       ├── _base.py                            # load + persist + iterate
│       └── run_{classification,extraction,summary,rag,agentic_rag,sql,pipeline}.py
├── src/
│   ├── api/routers/evals.py                    # /api/v1/evals/* endpoints
│   ├── db/models/eval_run.py                   # EvalRun + EvalResult ORM
│   └── db/repositories/evals_repo.py           # CRUD + trends
└── tests/evals/
    ├── test_evaluators_metric_based.py
    ├── test_evaluators_sql.py
    ├── test_evaluators_trajectory.py
    └── test_rubric_aggregate.py

frontend/
├── src/lib/api/evals.ts                        # Axios client
├── src/hooks/useEvals.ts                       # TanStack Query hooks
├── src/types/evals.ts                          # TS types
├── src/components/evals/
│   ├── ScoreCard.tsx
│   ├── MetricBreakdown.tsx
│   ├── ResultsTable.tsx
│   └── TrajectoryViewer.tsx
└── src/pages/
    ├── EvalsPage.tsx                           # /evals
    ├── EvalTrendsPage.tsx                      # /evals/trends
    └── EvalRunDetailPage.tsx                   # /evals/runs/:id
```
