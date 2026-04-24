"""Slides 11–16: datasets, runner, persistence, dashboard, CLI, summary."""

from __future__ import annotations

from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches

from .helpers import (
    add_bullets,
    add_rect,
    add_text,
    blank,
    code_block,
    footer,
    header_bar,
    kpi_tile,
    two_col_table,
)
from .theme import (
    ACCENT,
    BORDER,
    GREEN,
    INK,
    MONO,
    MUTED_BG,
    NAVY,
    ORANGE,
    PURPLE,
    SUBTLE,
    WHITE,
)


def slide_datasets(prs, page):
    s = blank(prs)
    header_bar(s, "Golden datasets + regression harvest", "Datasets")
    rows = [
        ("File", "Examples", "Target", "Purpose"),
        ("classification_golden.jsonl", "10", "50–100", "Category + calibration"),
        ("extraction_golden.jsonl", "15", "30–50", "8 LPA fields + verbatim source"),
        ("summary_golden.jsonl", "3", "30", "Reference summary + PE checklist"),
        ("rag_golden.jsonl", "10", "100", "Q&A + labelled relevant chunks"),
        ("sql_golden.jsonl", "9", "60", "NL→SQL + expected row-sets"),
        ("pipeline_golden.jsonl", "3", "10", "Full-pipeline gating correctness"),
        (
            "regression_corrections.jsonl",
            "auto",
            "—",
            "Auto-harvested user corrections",
        ),
        (
            "adversarial_synthetic.jsonl",
            "—",
            "—",
            "Synthesised perturbations (planned)",
        ),
    ]
    n = len(rows)
    row_h = Inches(0.42)
    cw = [Inches(4.10), Inches(1.30), Inches(1.30), Inches(5.50)]
    cx = [Inches(0.55), Inches(4.65), Inches(5.95), Inches(7.25)]
    y = Inches(1.55)
    for i, cells in enumerate(rows):
        is_header = i == 0
        fill = NAVY if is_header else (MUTED_BG if i % 2 == 0 else WHITE)
        fg = WHITE if is_header else INK
        for j, cell in enumerate(cells):
            add_rect(s, cx[j], y + row_h * i, cw[j], row_h, fill=fill, line=BORDER)
            add_text(
                s,
                cx[j] + Inches(0.10),
                y + row_h * i,
                cw[j] - Inches(0.18),
                row_h,
                cell,
                size=11,
                bold=is_header,
                color=fg,
                anchor=MSO_ANCHOR.MIDDLE,
                align=PP_ALIGN.LEFT if j not in (1, 2) else PP_ALIGN.CENTER,
            )

    yy = Inches(1.55) + row_h * n + Inches(0.30)
    add_rect(s, Inches(0.55), yy, Inches(12.20), Inches(1.30), fill=MUTED_BG)
    add_text(
        s,
        Inches(0.75),
        yy + Inches(0.10),
        Inches(11.8),
        Inches(0.40),
        "Closed-loop regression harvesting",
        size=14,
        bold=True,
        color=NAVY,
    )
    add_text(
        s,
        Inches(0.75),
        yy + Inches(0.50),
        Inches(11.8),
        Inches(0.75),
        "User correction in UI → long-term memory namespace → "
        "harvest-regressions → regression_corrections.jsonl. "
        "Next eval run replays them. New corrections become new tests automatically.",
        size=11,
        color=INK,
    )
    footer(s, page)


def slide_runner(prs, page):
    s = blank(prs)
    header_bar(s, "Runner pipeline (per stage)", "Execution model")
    code = """async def run_experiment(stage, dataset_file, predict, evaluators, ...):
    examples = load_examples(dataset_file, subset, tags)
    run_row  = await repo.create_run(stage, model, judge_model, git_sha, tags)

    for ex in examples:
        prediction = await predict(ex)              # production LLM call
        for key, fn in evaluators:
            result = await invoke(fn, prediction, ex) # sync OR async — both ok
            await repo.add_result(run_row.id, ex.id, key, result.score, ...)

    await repo.finalise_run(run_row, total, duration, summary_scores)
    return { "run_id", "summary_scores", "per_example" }
"""
    code_block(
        s, Inches(0.55), Inches(1.55), Inches(12.20), Inches(3.20), code, size=11
    )

    add_text(
        s,
        Inches(0.55),
        Inches(5.00),
        Inches(12),
        Inches(0.40),
        "Failure isolation",
        size=14,
        bold=True,
        color=NAVY,
    )
    add_bullets(
        s,
        Inches(0.55),
        Inches(5.40),
        Inches(12.20),
        Inches(1.60),
        [
            "DB unreachable (CI) → persistence disabled, run continues in-memory.",
            "predict() raises → recorded as { error } prediction; evaluators score against it.",
            "Evaluator raises → score=None + comment; other evaluators keep going.",
            "Stamped on every row: model · judge_model · git_sha · tags · duration.",
        ],
        size=12,
    )
    footer(s, page)


def slide_persistence(prs, page):
    s = blank(prs)
    header_bar(s, "Persistence — Alembic 004", "Schema & API")
    code = """eval_runs                              eval_results
  id              uuid pk                id              uuid pk
  stage           text                   run_id          uuid fk → eval_runs
  dataset_name    text                   example_id      text
  model           text                   evaluator_key   text
  judge_model     text                   score           float | NULL
  git_sha         text                   passed          bool  | NULL
  total_examples  int                    comment         text
  duration_seconds float                 prediction      jsonb
  status          text  (running|...)    expected        jsonb
  summary_scores  jsonb                  criteria_breakdown jsonb
  tags            jsonb                  INDEX(run_id, evaluator_key)
  created_at, updated_at
  INDEX(stage, created_at)
"""
    code_block(
        s, Inches(0.55), Inches(1.55), Inches(12.20), Inches(3.50), code, size=11
    )

    add_text(
        s,
        Inches(0.55),
        Inches(5.20),
        Inches(12),
        Inches(0.4),
        "REST API   (registered as /api/v1/evals/*)",
        size=14,
        bold=True,
        color=NAVY,
    )
    rows = [
        ("Method · Path", "Purpose"),
        ("GET /evals/overview", "Per-stage scorecards (last run + delta vs previous)."),
        ("GET /evals/runs?stage=", "Paginated runs, filterable by stage."),
        ("GET /evals/runs/{id}", "One run + all per-result rows."),
        ("POST /evals/runs", "Trigger a run (stage, subset?, tags?, model?). 202."),
        ("GET /evals/trends", "Time-series for (stage, evaluator_key)."),
    ]
    two_col_table(
        s,
        Inches(0.55),
        Inches(5.65),
        Inches(12.20),
        Inches(1.40),
        rows,
        col1_w_ratio=0.30,
    )
    footer(s, page)


def slide_dashboard(prs, page):
    s = blank(prs)
    header_bar(s, "Dashboard — /evals", "Frontend")
    add_text(
        s,
        Inches(0.55),
        Inches(1.55),
        Inches(12),
        Inches(0.4),
        "Three pages, one source of truth",
        size=14,
        bold=True,
        color=NAVY,
    )
    pages = [
        (
            "/evals",
            "Overview",
            ACCENT,
            [
                "Scorecard per stage.",
                "Primary metric + delta vs previous.",
                "Run-now button (202 background task).",
            ],
        ),
        (
            "/evals/trends",
            "Trends",
            PURPLE,
            [
                "Pick stage + evaluator.",
                "Time-series of summary score.",
                "Catches drift across model upgrades.",
            ],
        ),
        (
            "/evals/runs/:id",
            "Run detail",
            GREEN,
            [
                "Per-example × per-evaluator table.",
                "Trajectory viewer for agentic RAG.",
                "Raw prediction vs expected JSON.",
            ],
        ),
    ]
    x0, y = Inches(0.55), Inches(2.00)
    cw, ch, gap = Inches(4.05), Inches(3.50), Inches(0.10)
    for i, (path, title, c, lines) in enumerate(pages):
        x = x0 + (cw + gap) * i
        add_rect(s, x, y, cw, ch, fill=WHITE, line=BORDER)
        add_rect(s, x, y, cw, Inches(0.10), fill=c)
        add_text(
            s,
            x + Inches(0.20),
            y + Inches(0.20),
            cw - Inches(0.40),
            Inches(0.40),
            title,
            size=18,
            bold=True,
            color=NAVY,
        )
        add_text(
            s,
            x + Inches(0.20),
            y + Inches(0.65),
            cw - Inches(0.40),
            Inches(0.35),
            path,
            size=11,
            color=SUBTLE,
            font=MONO,
        )
        add_bullets(
            s,
            x + Inches(0.20),
            y + Inches(1.10),
            cw - Inches(0.40),
            ch - Inches(1.20),
            lines,
            size=12,
        )

    add_text(
        s,
        Inches(0.55),
        Inches(5.85),
        Inches(12),
        Inches(0.40),
        "Components: ScoreCard · MetricBreakdown · ResultsTable · "
        "TrajectoryViewer  (frontend/src/components/evals/)",
        size=11,
        color=SUBTLE,
    )
    footer(s, page)


def slide_cli(prs, page):
    s = blank(prs)
    header_bar(s, "CLI cheatsheet", "How to run")
    code = """# What stages exist + how many golden examples each has
uv run python -m backend.evals.cli list-stages

# Push every non-empty JSONL to LangSmith as pe-doc-intel/<stage>
uv run python -m backend.evals.cli sync-datasets

# Pull user corrections from long-term memory into regression set
uv run python -m backend.evals.cli harvest-regressions

# Run one stage on the first N examples
uv run python -m backend.evals.cli run --stage extraction --subset 5

# Run one stage filtered by tags
uv run python -m backend.evals.cli run --stage rag --tags single_hop numeric

# Run all stages
uv run python -m backend.evals.cli run --stage all
"""
    code_block(
        s, Inches(0.55), Inches(1.55), Inches(12.20), Inches(3.60), code, size=12
    )

    add_text(
        s,
        Inches(0.55),
        Inches(5.30),
        Inches(12),
        Inches(0.4),
        "Required env",
        size=14,
        bold=True,
        color=NAVY,
    )
    add_bullets(
        s,
        Inches(0.55),
        Inches(5.70),
        Inches(12.20),
        Inches(1.40),
        [
            "OPENAI_API_KEY — production model.",
            "DATABASE_URL — for run persistence (else in-memory).",
            "LANGSMITH_API_KEY (+ LANGCHAIN_TRACING_V2=true) — dataset sync + traces.",
            "EVAL_JUDGE_MODEL (optional) — override the judge tier.",
        ],
        size=12,
    )
    footer(s, page)


def slide_summary(prs, page):
    s = blank(prs)
    header_bar(s, "What this gives us", "Summary")
    kpis = [
        ("8", "LLM surfaces graded", ACCENT),
        ("4", "Evaluator layers", PURPLE),
        ("20+", "Built-in evaluators", GREEN),
        ("4", "YAML rubrics", ORANGE),
    ]
    x0 = Inches(0.55)
    tw, th, gap = Inches(2.95), Inches(1.55), Inches(0.20)
    for i, (val, label, c) in enumerate(kpis):
        kpi_tile(s, x0 + (tw + gap) * i, Inches(1.55), tw, th, val, label, color=c)

    add_text(
        s,
        Inches(0.55),
        Inches(3.40),
        Inches(12),
        Inches(0.4),
        "Operational benefits",
        size=15,
        bold=True,
        color=NAVY,
    )
    add_bullets(
        s,
        Inches(0.55),
        Inches(3.85),
        Inches(12.20),
        Inches(2.60),
        [
            "Pre-merge gate: deterministic metrics run in CI without API keys.",
            "Model-upgrade safety: trends per (stage, evaluator) catch regressions on day one.",
            "Calibration trust: ECE + judge_meta surface confidence drift, not just accuracy.",
            "Closed-loop learning: every UI correction becomes a new regression test.",
            "Provenance: every score row keeps prediction + expected + reasoning for audit.",
        ],
        size=13,
    )

    add_rect(s, Inches(0.55), Inches(6.50), Inches(12.20), Inches(0.55), fill=MUTED_BG)
    add_text(
        s,
        Inches(0.75),
        Inches(6.55),
        Inches(11.8),
        Inches(0.45),
        "Read more: docs/eval-framework.md   ·   Code: backend/evals/   ·   "
        "Tests: backend/tests/evals/   ·   Migration: alembic/versions/004_add_eval_runs.py",
        size=11,
        color=NAVY,
        anchor=MSO_ANCHOR.MIDDLE,
    )
    footer(s, page)
