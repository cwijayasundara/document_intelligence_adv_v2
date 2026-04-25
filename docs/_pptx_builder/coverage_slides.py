"""Slides 21–22: dataset coverage surface + forward roadmap."""

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
    kpi_tile,
)
from .theme import (
    ACCENT,
    GREEN,
    INK,
    MUTED_BG,
    NAVY,
    ORANGE,
    PURPLE,
    RED,
    SUBTLE,
)


def slide_coverage(prs, page):
    """Slide 21: Current coverage surface + extension pattern."""
    s = blank(prs)
    header_bar(s, "Coverage surface", "Golden datasets")

    kpis = [
        ("18", "classification", ACCENT),
        ("24", "extraction", PURPLE),
        ("9", "summary", GREEN),
        ("18", "rag", ORANGE),
        ("9", "sql", NAVY),
        ("3", "pipeline", RED),
    ]
    x0 = Inches(0.55)
    tw, th, gap = Inches(1.98), Inches(1.45), Inches(0.10)
    for i, (val, label, c) in enumerate(kpis):
        kpi_tile(s, x0 + (tw + gap) * i, Inches(1.55), tw, th, val, label, color=c)

    add_text(
        s,
        Inches(0.55),
        Inches(3.15),
        Inches(12.20),
        Inches(0.35),
        "Extension pattern — inline_content for reproducibility",
        size=14,
        bold=True,
        color=NAVY,
    )
    add_bullets(
        s,
        Inches(0.55),
        Inches(3.55),
        Inches(12.20),
        Inches(1.80),
        [
            "Golden records can point at parsed_path OR carry inline_content. "
            "Inline-content records are self-contained — no assets on disk, no "
            "Weaviate ingestion, no prior parse. Reproducible anywhere.",
            "Every record carries tags for subset runs: "
            "./evals.sh run --stage classification --tags adversarial.",
            "Negative tags (absent_field, hallucination_trap, explicit_none) "
            "pin the model's refusal / abstain behaviour, not just accuracy.",
            "Tag taxonomy is open-ended — add a new tag and start filtering on it.",
        ],
        size=12,
    )

    yy = Inches(5.70)
    add_rect(s, Inches(0.55), yy, Inches(12.20), Inches(1.35), fill=MUTED_BG)
    add_text(
        s,
        Inches(0.75),
        yy + Inches(0.10),
        Inches(11.80),
        Inches(0.35),
        "Recent coverage bump targets specific gaps",
        size=13,
        bold=True,
        color=NAVY,
    )
    add_text(
        s,
        Inches(0.75),
        yy + Inches(0.50),
        Inches(11.80),
        Inches(0.80),
        "classification +8 (capital call, PPM, tax K-1, advisory minutes, service agreements)   ·   "
        "extraction +9 (target_fund_size, vintage_year, key_person, NY law, Euro format, step-down fee)   ·   "
        "summary +6 (side letter, capital-call notice, short LPA, partial terms sheet, PPM)   ·   "
        "rag +8 (aggregation, negation, no-answer, date-bounded, fiduciary duties).",
        size=10.5,
        color=INK,
    )

    footer(s, page)


def slide_roadmap(prs, page):
    """Slide 22: Forward roadmap."""
    s = blank(prs)
    header_bar(s, "Roadmap", "What's next")

    add_text(
        s,
        Inches(0.55),
        Inches(1.45),
        Inches(12.20),
        Inches(0.45),
        "The framework is production-viable today. The roadmap below extends "
        "coverage depth and reduces the operational surface further.",
        size=12,
        color=SUBTLE,
    )

    card_w, card_h = Inches(3.95), Inches(2.40)
    col_x = [Inches(0.55), Inches(4.70), Inches(8.85)]
    row_y = [Inches(2.15), Inches(4.75)]
    cards = [
        (
            "Coverage depth",
            [
                "Grow classification 18 → 50 (more negative classes).",
                "Full adversarial_synthetic set (currently empty).",
                "Real-PDF fixtures for parse / extract stages.",
                "RAG: ingest 5+ doc types beyond LPA.",
            ],
            ACCENT,
        ),
        (
            "New evaluators",
            [
                "judge_meta → wire confidence calibration (ECE).",
                "Side-effect checks (ingest_node: Weaviate chunk count).",
                "Cost evaluator: tokens + $ per example, surfaced alongside quality.",
                "Latency SLO evaluator with p50/p95 buckets.",
            ],
            PURPLE,
        ),
        (
            "E2E pipeline",
            [
                "Seeded test DB + fixture PDFs.",
                "Mocked Reducto / OpenAI for hermetic runs.",
                "Checkpointed resume across the two review gates.",
                "Pipeline latency budget as part of the run contract.",
            ],
            GREEN,
        ),
        (
            "Closed-loop learning",
            [
                "Auto-promote high-correction namespaces to dedicated datasets.",
                "A/B on prompt/model — staged rollout gated by eval deltas.",
                "Regression drift alerts when a primary metric drops > 5 pts.",
            ],
            ORANGE,
        ),
        (
            "Upstream cleanups",
            [
                "Migrate off deprecated ragas.evaluate() fully.",
                "Replace authlib.jose → joserfc.",
                "Drop MemoryEntry.user_id ORM drift or add the column.",
                "datetime.utcnow() → datetime.now(UTC) in repositories.",
            ],
            RED,
        ),
        (
            "Dashboard polish",
            [
                "Per-tag sub-views (filter to only 'adversarial' on a stage).",
                "Inline per-example drill-down with prediction / expected diff.",
                "Export run + per-example results as CSV / JSON.",
                "Retention + storage policy for eval_results JSONB.",
            ],
            NAVY,
        ),
    ]
    for i, (title, bullets, accent) in enumerate(cards):
        x = col_x[i % 3]
        y = row_y[i // 3]
        card(s, x, y, card_w, card_h, title, bullets, accent=accent)

    footer(s, page)
