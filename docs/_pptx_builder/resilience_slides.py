"""Slides 17–18: resilience / fault isolation, and the long-term memory
+ regression-harvest loop."""

from __future__ import annotations

from pptx.util import Inches

from .helpers import (
    add_bullets,
    add_rect,
    add_text,
    blank,
    card,
    footer,
    header_bar,
)
from .theme import (
    ACCENT,
    BORDER,
    GREEN,
    MUTED_BG,
    NAVY,
    ORANGE,
    PURPLE,
    RED,
    SUBTLE,
    WHITE,
)


def slide_resilience(prs, page):
    """Slide 17: Fault isolation + durability in the runner + evaluator layers."""
    s = blank(prs)
    header_bar(s, "Resilience & fault isolation", "Durability")
    add_text(
        s,
        Inches(0.55),
        Inches(1.45),
        Inches(12.20),
        Inches(0.45),
        "Every failure mode is contained to the smallest unit that can express "
        "it — one evaluator, one example, or one run — so one bad call can't "
        "take down a 20-minute suite.",
        size=12,
        color=SUBTLE,
    )

    card_w, card_h = Inches(3.95), Inches(2.25)
    col_x = [Inches(0.55), Inches(4.70), Inches(8.85)]
    row_y = [Inches(2.10), Inches(4.55)]

    cards = [
        (
            "Idempotent engine lifecycle",
            [
                "init_engine() returns early if already bound",
                "dispose_engine() in try/finally closes the asyncpg pool",
                "Cures the 'unclosed connection' warning storm from re-init per example",
            ],
            ACCENT,
        ),
        (
            "JSON-safe coercion at the DB boundary",
            [
                "_json_safe() scrubs prediction / expected / criteria",
                "Converts LangChain BaseMessage via .model_dump()",
                "datetime → isoformat(); NaN/Inf → None",
                "Keeps JSONB writes from rejecting the whole run",
            ],
            GREEN,
        ),
        (
            "Non-finite score filtering",
            [
                "Per-example: math.isfinite(score) gate",
                "Per-run: summary_scores drops any evaluator with non-finite values",
                "One flaky ragas NaN no longer poisons the run",
            ],
            PURPLE,
        ),
        (
            "Per-evaluator exception containment",
            [
                "Each evaluator wrapped in try/except BLE001",
                "Failure recorded as {score: None, comment: 'error: …'}",
                "Other evaluators for the same example still run",
            ],
            ORANGE,
        ),
        (
            "LLM call timeout + retry cap",
            [
                "get_llm(timeout=90, max_retries=3) from settings",
                "Bounds OpenAI 502 + Retry-After: 60 stalls",
                "Caller records the failure and moves on",
            ],
            RED,
        ),
        (
            "Run-status truthfulness",
            [
                "except BaseException → rollback + finalise_run(status='failed')",
                "No orphaned 'running' rows in eval_runs",
                "Dashboard deltas remain comparable even after a bad run",
            ],
            NAVY,
        ),
    ]
    for i, (title, bullets, accent) in enumerate(cards):
        x = col_x[i % 3]
        y = row_y[i // 3]
        card(s, x, y, card_w, card_h, title, bullets, accent=accent)

    footer(s, page)


def slide_memory(prs, page):
    """Slide 18: SqlAlchemyMemoryStore + regression harvest loop."""
    s = blank(prs)
    header_bar(s, "Long-term memory & the dogfood loop", "Persistence")
    add_text(
        s,
        Inches(0.55),
        Inches(1.45),
        Inches(12.20),
        Inches(0.45),
        "Corrections written by the API server now survive across processes, "
        "so the harvest CLI turns real user feedback into new regression tests.",
        size=12,
        color=SUBTLE,
    )

    # Left column: architecture
    add_text(
        s,
        Inches(0.55),
        Inches(2.05),
        Inches(6.00),
        Inches(0.35),
        "SqlAlchemyMemoryStore",
        size=15,
        bold=True,
        color=NAVY,
    )
    add_bullets(
        s,
        Inches(0.55),
        Inches(2.45),
        Inches(6.00),
        Inches(2.80),
        [
            "Backs the existing memory_entries table — no new schema.",
            "aput / aget / asearch duck-typed against LangGraph BaseStore.",
            "Tuple namespaces encoded with \\x1e separator for prefix scans.",
            "Prefix search: namespace = prefix OR namespace LIKE prefix||\\x1e||'%'.",
            "Returns LangGraph Item / SearchItem objects for .value / .key / .created_at access.",
        ],
        size=11.5,
    )

    # Right column: harvest flow diagram
    add_text(
        s,
        Inches(7.00),
        Inches(2.05),
        Inches(5.75),
        Inches(0.35),
        "Harvest loop",
        size=15,
        bold=True,
        color=NAVY,
    )
    diagram_lines = [
        "UI: user corrects a classification / extraction",
        "⬇",
        "API: save_correction('classification', key, data)",
        "⬇",
        "memory_entries INSERT … ON CONFLICT (namespace, key) DO UPDATE",
        "⬇",
        "evals.sh harvest-regressions  (separate process)",
        "⬇",
        "load_all_corrections(prefix) → SearchItem list",
        "⬇",
        "regression_corrections.jsonl  →  new eval examples",
    ]
    add_rect(
        s,
        Inches(7.00),
        Inches(2.45),
        Inches(5.75),
        Inches(2.85),
        fill=MUTED_BG,
        line=BORDER,
    )
    add_bullets(
        s,
        Inches(7.15),
        Inches(2.55),
        Inches(5.55),
        Inches(2.70),
        diagram_lines,
        size=10.5,
        line_spacing=1.10,
    )

    # Footer card — fallback + diagnostic
    yy = Inches(5.50)
    add_rect(s, Inches(0.55), yy, Inches(12.20), Inches(1.40), fill=WHITE, line=BORDER)
    add_rect(s, Inches(0.55), yy, Inches(0.08), Inches(1.40), fill=ACCENT)
    add_text(
        s,
        Inches(0.80),
        yy + Inches(0.10),
        Inches(11.80),
        Inches(0.40),
        "Fallback & diagnostic behaviour",
        size=13,
        bold=True,
        color=NAVY,
    )
    add_bullets(
        s,
        Inches(0.80),
        yy + Inches(0.50),
        Inches(11.80),
        Inches(0.85),
        [
            "get_memory_store() probes the DB with SELECT 1 and falls back to "
            "InMemoryStore only when Postgres is unreachable (with an explicit warning).",
            "is_ephemeral_store() surfaces the downgrade, and harvest-regressions "
            "logs a warning when an empty harvest coincides with the fallback — so "
            "'0 corrections' never silently masks a config problem.",
        ],
        size=11,
    )

    footer(s, page)
