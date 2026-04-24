# Evaluation Framework

Production-grade eval framework for the PE Document Intelligence platform. Covers every LLM
touchpoint with four evaluator layers — **metric-based**, **LLM-as-judge**, **rubric-based**,
and **trajectory** — and surfaces results to LangSmith + a local `/evals` dashboard.

## Directory layout

```
backend/evals/
├── datasets/          # Golden JSONL files, one per pipeline stage
├── fixtures/          # PDFs + cached parsed markdown
├── evaluators/        # LangSmith-compatible evaluator callables
├── rubrics/           # YAML rubric definitions (multi-criterion)
├── runners/           # Per-stage experiment runners
├── cli.py             # `python -m evals.cli …`
├── dataset_sync.py    # Push / pull datasets to LangSmith
└── regression_harvest.py  # Mine `long_term` memory corrections → regression set
```

## Datasets

Each JSONL file holds one golden example per line. Example keys are stage-specific; common
keys are `id`, `tags`, `source`, and `notes`.

| File | Purpose | Target size |
|---|---|---|
| `classification_golden.jsonl` | Category assignment + calibration | 50–100 |
| `extraction_golden.jsonl` | 8 LPA fields + verbatim source | 30–50 |
| `summary_golden.jsonl` | Reference summaries + PE checklist | 30 |
| `rag_golden.jsonl` | Q&A + labelled relevant chunks | 100 |
| `sql_golden.jsonl` | NL→SQL + expected row-sets | 60 |
| `pipeline_golden.jsonl` | Full-pipeline gating correctness | 10 |
| `regression_corrections.jsonl` | Auto-harvested user corrections | — |
| `adversarial_synthetic.jsonl` | Synthesised perturbations | — |

## Running evals

The repo-root wrapper `./evals.sh` forwards to the CLI using the backend
venv, so it works from any cwd. The commands below also work with the bare
CLI when run from `backend/` (`uv run python -m evals.cli …`).

```bash
# Sync current datasets to LangSmith (creates/updates a dataset per stage).
./evals.sh sync-datasets

# Run one stage end-to-end against a 5-example subset.
./evals.sh run --stage extraction --subset 5

# Run the full suite (slow, $$). Prints a consolidated summary table
# (status + examples + duration + primary-metric score per stage) at the end
# and exits non-zero if any stage failed.
./evals.sh run --stage all

# Same but on a small subset — fast smoke test before a full run.
./evals.sh run --stage all --subset 3

# Harvest recent user corrections into a regression dataset.
./evals.sh harvest-regressions
```

All runs stream progress to stdout and are traced to the LangSmith project
`pe-doc-intel-evals`. Aggregate scores + per-example results persist to the
`eval_runs`, `eval_examples`, and `eval_results` tables so the dashboard at `/evals`
can surface history and trends.

## Environment

Required:
- `OPENAI_API_KEY` — production models.
- `LANGSMITH_API_KEY` — trace + dataset persistence.

Optional (recommended):
- `LANGCHAIN_TRACING_V2=true`
- `LANGCHAIN_PROJECT=pe-doc-intel-evals`
- `EVAL_JUDGE_MODEL` — override the judge model (default: one tier stronger than
  `OPENAI_MODEL`).
- `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:6006/v1/traces` — ship traces to
  local Arize Phoenix for live debugging.
