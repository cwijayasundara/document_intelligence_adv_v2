"""Slides 19–20: single-command entry points + pipeline-stage scope."""

from __future__ import annotations

from pptx.util import Inches

from .helpers import (
    add_bullets,
    add_rect,
    add_text,
    blank,
    code_block,
    footer,
    header_bar,
    two_col_table,
)
from .theme import (
    INK,
    MUTED_BG,
    NAVY,
    SUBTLE,
    WHITE,
)


def slide_deployment(prs, page):
    """Slide 19: Single-command entry points + sitecustomize + CI wiring."""
    s = blank(prs)
    header_bar(s, "Deployment & single-command runs", "Ops")
    add_text(
        s,
        Inches(0.55),
        Inches(1.45),
        Inches(12.20),
        Inches(0.45),
        "One wrapper, any cwd, same venv. Works locally and in CI without "
        "path-juggling or PYTHONPATH exports.",
        size=12,
        color=SUBTLE,
    )

    # Left: the wrapper
    add_text(
        s,
        Inches(0.55),
        Inches(2.05),
        Inches(6.00),
        Inches(0.35),
        "./evals.sh  →  backend/ + uv run",
        size=14,
        bold=True,
        color=NAVY,
    )
    code_block(
        s,
        Inches(0.55),
        Inches(2.45),
        Inches(6.00),
        Inches(1.70),
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'cd "$(cd "$(dirname "$0")" && pwd)/backend"\n'
        'exec uv run python -m evals.cli "$@"\n',
        size=10,
    )
    add_text(
        s,
        Inches(0.55),
        Inches(4.20),
        Inches(6.00),
        Inches(0.30),
        "Why the chdir? uv anchors to the nearest pyproject.toml; without "
        "it, uv from the repo root falls back to the base Python interpreter.",
        size=10,
        color=SUBTLE,
    )

    # Right: sitecustomize
    add_text(
        s,
        Inches(7.00),
        Inches(2.05),
        Inches(5.75),
        Inches(0.35),
        "sitecustomize.py  (written by init.sh)",
        size=14,
        bold=True,
        color=NAVY,
    )
    code_block(
        s,
        Inches(7.00),
        Inches(2.45),
        Inches(5.75),
        Inches(1.70),
        "import os, sys\n"
        "_REPO_ROOT = '/…/document_intelligence_adv_v2'\n"
        "_BACKEND   = os.path.join(_REPO_ROOT, 'backend')\n"
        "for p in (_REPO_ROOT, _BACKEND):\n"
        "    if os.path.isdir(p) and p not in sys.path:\n"
        "        sys.path.insert(0, p)\n",
        size=10,
    )
    add_text(
        s,
        Inches(7.00),
        Inches(4.20),
        Inches(5.75),
        Inches(0.30),
        "Why not a .pth file? Python 3.13 skips .pth files marked with the "
        "macOS UF_HIDDEN flag — which uv sets on everything in .venv/.",
        size=10,
        color=SUBTLE,
    )

    # Bottom: CLI subcommands
    yy = Inches(4.85)
    add_text(
        s,
        Inches(0.55),
        yy,
        Inches(12.20),
        Inches(0.35),
        "CLI surface",
        size=14,
        bold=True,
        color=NAVY,
    )
    rows = [
        ("Command", "Purpose"),
        ("./evals.sh list-stages", "Print stages + example counts."),
        ("./evals.sh sync-datasets", "Push golden JSONLs to LangSmith."),
        ("./evals.sh run --stage <stage> [--subset N] [--tags …]", "Run one stage."),
        (
            "./evals.sh run --stage all [--subset N]",
            "Run every stage + consolidated summary.",
        ),
        (
            "./evals.sh harvest-regressions",
            "Write regression_corrections.jsonl from memory_entries.",
        ),
    ]
    two_col_table(
        s,
        Inches(0.55),
        Inches(5.25),
        Inches(12.20),
        Inches(1.85),
        rows,
        col1_w_ratio=0.40,
    )

    footer(s, page)


def slide_pipeline_scope(prs, page):
    """Slide 20: What pipeline stage tests (and what it doesn't)."""
    s = blank(prs)
    header_bar(s, "Pipeline stage — scope & rationale", "Design choice")
    add_text(
        s,
        Inches(0.55),
        Inches(1.45),
        Inches(12.20),
        Inches(0.45),
        "Full E2E would need seeded DB rows, real PDFs, live Reducto/OpenAI "
        "and a checkpointer with thread_id. The pipeline eval instead verifies "
        "gate routing + graph traversal — the regressions it can actually catch.",
        size=12,
        color=SUBTLE,
    )

    left_x, right_x = Inches(0.55), Inches(6.90)
    col_w = Inches(5.85)

    add_rect(s, left_x, Inches(2.10), col_w, Inches(0.50), fill=NAVY)
    add_text(
        s,
        left_x + Inches(0.20),
        Inches(2.20),
        col_w - Inches(0.40),
        Inches(0.30),
        "Catches",
        size=13,
        bold=True,
        color=WHITE,
    )
    add_bullets(
        s,
        left_x + Inches(0.20),
        Inches(2.75),
        col_w - Inches(0.40),
        Inches(3.30),
        [
            "Inverted gate comparison (>= vs <=).",
            "Wrong state field read (parse_confidence vs parse_confidence_pct).",
            "Graph edge drift — classify placed before summarize, etc.",
            "await_*_review node inserted into the wrong branch.",
            "Threshold regression — default 90% moved without updating expectations.",
        ],
        size=11.5,
    )

    add_rect(s, right_x, Inches(2.10), col_w, Inches(0.50), fill=MUTED_BG)
    add_text(
        s,
        right_x + Inches(0.20),
        Inches(2.20),
        col_w - Inches(0.40),
        Inches(0.30),
        "Doesn't catch (out of scope)",
        size=13,
        bold=True,
        color=NAVY,
    )
    add_bullets(
        s,
        right_x + Inches(0.20),
        Inches(2.75),
        col_w - Inches(0.40),
        Inches(3.30),
        [
            "parse_node Reducto integration regressions.",
            "classify_node / extract_node prompt drift — covered by their own evals.",
            "ingest_node Weaviate schema mismatches.",
            "Real latency / throughput — that's observability, not an eval.",
            "End-to-end golden outputs on real PDFs — needs a soak environment.",
        ],
        size=11.5,
    )

    # Bottom: execution model
    yy = Inches(6.20)
    add_rect(s, Inches(0.55), yy, Inches(12.20), Inches(0.80), fill=MUTED_BG)
    add_text(
        s,
        Inches(0.75),
        yy + Inches(0.10),
        Inches(11.80),
        Inches(0.30),
        "Execution model",
        size=12,
        bold=True,
        color=NAVY,
    )
    add_text(
        s,
        Inches(0.75),
        yy + Inches(0.40),
        Inches(11.80),
        Inches(0.40),
        "_synthesize_state(example)  →  route_after_parse (pure fn)  →  "
        "route_after_extract (pure fn)  →  traverse graph edges  →  stages_reached list.   "
        "≈1s per run, no LLM, no DB, no files.",
        size=11,
        color=INK,
    )

    footer(s, page)
