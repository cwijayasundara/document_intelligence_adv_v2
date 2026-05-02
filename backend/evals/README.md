# Evaluation Framework

Production-grade eval framework for the PE Document Intelligence platform. Covers every LLM
touchpoint with four evaluator layers — **metric-based**, **LLM-as-judge**, **rubric-based**,
and **trajectory** — and surfaces results to LangSmith + a local `/evals` dashboard.

## Directory layout

```
backend/evals/
├── datasets/             # Golden JSONL files, one per pipeline stage
├── fixtures/             # PDFs + cached parsed markdown
├── evaluators/           # LangSmith-compatible evaluator callables
├── rubrics/              # YAML rubric definitions (multi-criterion)
├── runners/              # Per-stage experiment runners
├── data_synthesizer/     # Generate-then-verify golden datasets from parsed text
│   ├── synthesizers/     #   one module per kind: rag, extraction, classification,
│   │                     #   summary, sql, pipeline
│   ├── corpus.py         #   parsed-doc loader + chunker
│   ├── judge.py          #   judge wrapper with cost meter + audit log
│   ├── writer.py         #   JSONL writer (append | overwrite | dry-run)
│   └── README.md         #   full reference for the synthesizer
├── cli.py                # `python -m evals.cli …`
├── dataset_sync.py       # Push / pull datasets to LangSmith
└── regression_harvest.py # Mine `long_term` memory corrections → regression set
```

## Datasets

Each JSONL file holds one golden example per line. Example keys are stage-specific; common
keys are `id`, `tags`, `source`, and `notes`.

| File | Purpose | Synth kind | Target size |
|---|---|---|---|
| `classification_golden.jsonl` | Category assignment + calibration | `classification` | 50–100 |
| `extraction_golden.jsonl` | Field-level extraction + verbatim source | `extraction` | 30–50 |
| `summary_golden.jsonl` | Reference summaries + grounded checklist | `summary` | 30 |
| `rag_golden.jsonl` | Q&A + labelled relevant chunks | `rag` | 100 |
| `sql_golden.jsonl` | NL→SQL + expected row-sets | `sql` | 60 |
| `pipeline_golden.jsonl` | Full-pipeline gating correctness | `pipeline` (deterministic) | 10 |
| `regression_corrections.jsonl` | Auto-harvested user corrections | n/a — `evals.sh harvest-regressions` | — |
| `adversarial_synthetic.jsonl` | Synthesised perturbations | n/a (manual) | — |

## Generating golden datasets

`backend/evals/data_synthesizer` produces golden JSONL using a generate-then-verify
loop over an LLM judge. The synthesizers are **domain-agnostic**: prompts use
a neutral persona, and per-kind specifics (categories for classification,
fields for extraction, etc.) come from CLI flags rather than hardcoded
PE/LPA lists. See `data_synthesizer/README.md` for full reference.

```bash
# List supported kinds.
./evals.sh synth list-kinds

# Dry-run: writes <out>.proposed.jsonl, never touches the live golden file.
./evals.sh synth --kind rag,extraction --inputs backend/data/parsed --n 20 --mode dry-run

# Tune the judge persona for any vertical via --domain-hint.
./evals.sh synth --kind rag,extraction,summary \
  --inputs backend/data/parsed --n 20 \
  --domain-hint "private equity LPAs and amendments"

# Classification needs categories (comma-separated; "Name: description" optional).
./evals.sh synth --kind classification --inputs backend/data/parsed --n 30 \
  --categories "Limited Partnership Agreement,Subscription Agreement,Side Letter,Other"

# Pin extraction fields instead of letting the LLM discover them.
./evals.sh synth --kind extraction --inputs backend/data/parsed --n 20 \
  --fields ./fields.json   # [{"field_name":"fund_name","data_type":"string"}, ...]

# Cost guardrail — abort once the rough estimate hits the cap.
./evals.sh synth --kind rag --inputs backend/data/parsed --n 50 --max-cost-usd 5.0

# Promote proposals: switch dry-run -> overwrite (or append).
./evals.sh synth --kind rag --inputs backend/data/parsed --n 50 --mode overwrite
```

Notes:
- `pipeline` is fully deterministic (no judge calls, no API cost).
- `sql` is schema-driven (frozen Postgres description in
  `data_synthesizer/synthesizers/_sql_fixtures.py`); `--inputs` is required
  by the CLI but ignored.
- Every judge call is logged to
  `data_synthesizer/.synth_logs/audit_YYYYMMDD.jsonl` (gitignored). Set
  `SYNTH_DISABLE_AUDIT_LOG=1` to opt out.

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
