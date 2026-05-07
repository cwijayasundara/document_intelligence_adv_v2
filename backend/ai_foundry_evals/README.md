# Azure AI Foundry Evaluation (parallel package)

Runs alongside `backend/evals/`. **Does not replace it** — adds the evaluators
and synthetic-data simulators that Foundry provides natively and the existing
framework does not.

## What this package adds

| Capability | Foundry built-in | Why it's not in `backend/evals/` |
|---|---|---|
| Hate / unfairness / sexual / violence / self-harm | `builtin.{hate_unfairness,sexual,violence,self_harm}` | no equivalent today |
| Copyrighted content detection | `builtin.protected_material` | no equivalent |
| **XPIA** indirect-attack jailbreak detection | `builtin.indirect_attack` | no equivalent |
| Insecure-code generation | `builtin.code_vulnerability` | no equivalent |
| PII / hallucinated personal attributes | `builtin.ungrounded_attributes` | no equivalent |
| Agent task adherence | `builtin.task_adherence` | partial overlap with rubric |
| Agent intent resolution | `builtin.intent_resolution` | no equivalent |
| Tool-call quality (selection, params) | `builtin.tool_call_accuracy`, `builtin.tool_selection` | covered loosely by `evaluators/trajectory.py` |
| Optimal action sequence | `builtin.task_navigation_efficiency` | covered loosely by `trajectory_order` |
| Retrieval composite (Fidelity / NDCG / XDCG / MaxRel / Holes) | `builtin.document_retrieval` | only Recall@K / MRR / nDCG@K today |
| Adversarial corpora (8 scenarios) | `AdversarialSimulator` | empty `adversarial_synthetic.jsonl` slot |
| UPIA / XPIA jailbreak corpora | `Direct/IndirectAttackSimulator` | no equivalent |

## What stays in `backend/evals/` (intentionally not migrated)

- `metric_based/*` — already free, fast, deterministic.
- `llm_judge/*` — `groundedness`, `relevance`, `retrieval` already covered by
  `faithfulness.py`, `relevance.py`, `ragas_triad.py`. Migrating is even-swap.
- `data_synthesizer/synthesizers/*` — domain-grounded RAG / extraction /
  classification / summary / SQL / pipeline generation with verifier loop.
  Foundry's `Simulator` only generates query/response pairs against your
  callback; it does not produce labelled extraction fields, classification
  labels, PE checklists, NL-SQL pairs, or pipeline-gate scenarios.
- `judge_meta_calibration` — grades the production Judge node from traces,
  not a static dataset; no Foundry analogue.
- SQL row-set execution check — Foundry custom-code evaluators run in a
  no-network sandbox and cannot hit Postgres.
- `regression_harvest.py` — pulls from `long_term` memory store. Stays local;
  the resulting JSONL can still be uploaded.

## Layout

```
backend/ai_foundry_evals/
├── settings.py              # AZURE_AI_PROJECT_ENDPOINT, deployment, project trio
├── client.py                # AIProjectClient + OpenAI evals client (lazy)
├── criteria.py              # testing_criteria builders for each used built-in
├── adapter.py               # backend/evals → Foundry row shapes
├── cli.py                   # python -m ai_foundry_evals.cli ...
├── agent/
│   └── message_adapter.py   # LangChain → OpenAI messages + tool_definitions
├── runners/
│   ├── _base.py             # submit() — create eval, post run, poll, fetch items
│   ├── run_safety.py        # 8 safety evaluators on a stage's outputs
│   ├── run_agent.py         # 4 agent evaluators on agentic_rag
│   └── run_retrieval_quality.py  # document_retrieval composite
└── simulators/
    ├── _target.py           # default callback that drives the production RAG
    ├── adversarial.py       # AdversarialSimulator wrapper (8 scenarios)
    └── jailbreak.py         # Direct (UPIA) + Indirect (XPIA) attack
```

## Setup

```bash
# Optional dep group (keeps default backend lean)
uv pip install -e backend[foundry]

# Auth
az login                                  # for DefaultAzureCredential

# Required
export AZURE_AI_PROJECT_ENDPOINT="https://<account>.services.ai.azure.com/api/projects/<project>"
export AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-5-mini"

# Required only for simulators (AdversarialSimulator / Direct / Indirect)
export AZURE_AI_SUBSCRIPTION_ID="..."
export AZURE_AI_RESOURCE_GROUP="..."
export AZURE_AI_PROJECT_NAME="..."
```

> Hosted safety evaluators and adversarial simulators are region-bound:
> **East US 2 / France Central / UK South / Sweden Central**.

## Run

```bash
# Risk / safety on each stage's outputs
./foundry_evals.sh safety --stage rag --subset 5
./foundry_evals.sh safety --stage summary --subset 5
./foundry_evals.sh safety --stage agentic_rag --subset 5

# Agent evaluators (TaskAdherence, IntentResolution, ToolCallAccuracy, ToolSelection)
./foundry_evals.sh agent --subset 5
# Add navigation efficiency (requires expected_tools on each example)
./foundry_evals.sh agent --subset 5 --with-navigation --matching-mode in_order_match

# Document retrieval composite — NDCG / XDCG / Fidelity / MaxRel / Holes
./foundry_evals.sh doc-retrieval --subset 10

# Generate adversarial corpora (writes datasets/adversarial_<scenario>.jsonl)
./foundry_evals.sh sim adversarial --scenario qa --n 50
./foundry_evals.sh sim adversarial --scenario summarization --n 30
./foundry_evals.sh sim adversarial --scenario protected_material --n 30

# Generate jailbreak corpora
./foundry_evals.sh sim jailbreak --type indirect --n 30   # XPIA
./foundry_evals.sh sim jailbreak --type direct --n 30     # UPIA (baseline + jailbroken)
```

Each evaluator run prints `eval_id`, `run_id`, `status`, `report_url`, and the
number of per-item results. The report URL opens the Foundry portal view.

## How rows are built

Foundry's data_mapping syntax is `{{item.<field>}}`. The adapter pulls the
existing `_predict()` from the relevant `evals/runners/run_*.py` and maps:

- `safety` rows → `{query, response, context}` with `context` joined from
  retrieved chunks (or summary inputs).
- `agent` rows → `{query, response, tool_definitions}` where `query` and
  `response` are OpenAI message arrays, and `tool_definitions` is built from
  the production agent's LangChain tools (`src.rag.agent._create_tools`).
- `doc-retrieval` rows → `{retrieval_ground_truth, retrieved_documents}`,
  labelling each retrieved chunk as relevant (level 4) iff any
  `expected_relevant_chunk_substrings` entry appears in it.

## Why parallel, not merged

- Existing harness is OpenAI-direct + LangSmith + Postgres. Foundry is
  cloud-orchestrated through Azure OpenAI. Forcing both into one runner
  couples local dev to Azure auth.
- Foundry submits run remotely (seconds to minutes). The current
  metric-based evaluators run in microseconds. Different latency regimes
  belong on different runners.
- The current framework gates CI today. Adding Foundry as a separate CLI
  lets you opt in per-PR or nightly without destabilising
  `evals.sh run --stage all`.

## Next steps (not implemented)

- Sync Foundry `output_items` into the local `eval_runs` / `eval_results`
  tables so the `/evals` dashboard surfaces both backends.
- Register the YAML rubrics under `backend/evals/rubrics/` as Foundry
  prompt-based custom evaluators (one-time portal task).
- Wire `--with-navigation` once `expected_tools` is populated on the agentic
  golden set with `expected_actions` matching the OpenAI-style schema.
