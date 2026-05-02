# Data Synthesizer

Generate golden eval datasets from parsed source documents using a
two-model generate-then-verify loop. Output JSONL is drop-in compatible with
the runners under `evals/runners/`.

The synthesizers are **domain-agnostic**: prompts use a neutral
domain-expert persona, and per-kind specifics (categories for
classification, fields for extraction) come from CLI flags rather than
hardcoded lists. Tune via `--domain-hint`.

## Supported kinds

| Kind | Output file | Inputs | Uses LLM judge |
|---|---|---|---|
| `rag` | `datasets/rag_golden.jsonl` | parsed markdown/txt | yes |
| `extraction` | `datasets/extraction_golden.jsonl` | parsed markdown/txt | yes |
| `classification` | `datasets/classification_golden.jsonl` | parsed markdown/txt | yes |
| `summary` | `datasets/summary_golden.jsonl` | parsed markdown/txt | yes |
| `sql` | `datasets/sql_golden.jsonl` | none (schema-driven; `--inputs` ignored) | yes |
| `pipeline` | `datasets/pipeline_golden.jsonl` | parsed markdown/txt | no (deterministic) |

Notes:
- `sql` ignores source documents — it generates NL/SQL pairs against a frozen
  description of the analytics schema (`synthesizers/_sql_fixtures.py`). It
  always emits the canonical refusal scenarios first, then top-up positives.
- `pipeline` is fully deterministic — it composes three canonical gate
  scenarios (happy-path, extraction-review, parse-review) per source doc.
  No judge calls, no API cost.
- `regression_corrections.jsonl` is produced by `evals.sh harvest-regressions`,
  not by this synthesizer.

## Quick start

```bash
# List available kinds.
./evals.sh synth list-kinds

# Dry-run RAG synth against parsed fixtures (writes <out>.proposed.jsonl).
./evals.sh synth --kind rag \
  --inputs backend/data/parsed \
  --n 20 \
  --mode dry-run

# Append verified rows to the live golden file.
./evals.sh synth --kind extraction \
  --inputs backend/data/parsed \
  --n 30 \
  --mode append \
  --max-cost-usd 5.0

# Multi-kind in one pass (each kind goes to its default file).
./evals.sh synth --kind rag,extraction --inputs backend/data/parsed --n 20

# Classification needs categories. Names only, or "Name: description":
./evals.sh synth --kind classification \
  --inputs backend/data/parsed --n 30 \
  --categories "Invoice: AR doc with line items,Receipt: payment confirmation,Other"

# Domain hint nudges every prompt (rag/extraction/classification/summary):
./evals.sh synth --kind rag,extraction,summary \
  --inputs backend/data/parsed --n 20 \
  --domain-hint "private equity LPAs"

# Pin extraction fields instead of letting the LLM discover them:
echo '[{"field_name":"invoice_number","data_type":"string"},
       {"field_name":"total_amount","data_type":"currency"}]' > /tmp/fields.json
./evals.sh synth --kind extraction \
  --inputs backend/data/parsed --n 20 --fields /tmp/fields.json
```

## Generic vs vertical-specific

| Knob | Effect |
|---|---|
| (no flag) | Neutral prompts. RAG/summary work out of the box; extraction discovers fields per doc; classification REQUIRES `--categories`. |
| `--domain-hint "<text>"` | Free-text injected into generator prompts ("private equity LPAs", "medical case reports", "AR invoices"). Optional. |
| `--categories "Name1,Name2: desc,Other"` | Required for kind=classification. Comma-separated; descriptions optional after a colon. |
| `--fields path/to/fields.json` | Optional schema for kind=extraction. Each entry: `{"field_name": str, "data_type": str}`. Without it, extraction runs in *discovery* mode. |

## How it works

1. **Corpus loader** (`corpus.py`) reads files/dirs/globs and returns a
   normalised `ParsedDoc`. RAG also chunks via the production
   `src.rag.chunker.DocumentChunker` so generated questions are tied to the
   chunks the retriever actually returns.
2. **Synthesizer** (`synthesizers/<kind>.py`) prompts the judge model to
   generate a candidate row, then runs a separate verification call to drop
   anything not entailed by the source. Each row carries a `synth` block
   with provenance.
3. **Writer** (`writer.py`) validates each row, dedupes by stage-specific
   keys, and supports `append | overwrite | dry-run`. Rejected rows go to
   `<out>.rejects.jsonl` with the failure reason.

## Modes

- `dry-run` (default) — writes proposals to `<out>.proposed.jsonl`, never
  touches the live golden file. Use for review.
- `append` — keeps existing rows, dedupes, appends new ones.
- `overwrite` — replaces the golden file.

## Cost & safety

- `--max-cost-usd` aborts the run cleanly once the rough estimate is reached.
- `--concurrency` caps parallel judge calls.
- Every judge call is logged to `data_synthesizer/.synth_logs/audit_YYYYMMDD.jsonl`
  (set `SYNTH_DISABLE_AUDIT_LOG=1` to opt out).
- Generator and verifier are independent passes; the judge model defaults to
  one tier above `OPENAI_MODEL` (see `evaluators/llm_judge/_base.py`).
