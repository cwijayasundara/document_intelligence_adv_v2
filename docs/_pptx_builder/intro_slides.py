"""Slides 1–5: title, motivation, architecture, scope, and evaluator taxonomy."""

from __future__ import annotations

from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches

from .helpers import (
    add_bullets,
    add_rect,
    add_text,
    blank,
    card,
    footer,
    header_bar,
    make_arrow,
    three_col_table,
)
from .theme import (
    ACCENT,
    BORDER,
    GREEN,
    INK,
    NAVY,
    ORANGE,
    PURPLE,
    RED,
    SLIDE_H,
    SLIDE_W,
    SUBTLE,
    WHITE,
)


def slide_title(prs):
    s = blank(prs)
    add_rect(s, Inches(0), Inches(0), SLIDE_W, SLIDE_H, fill=NAVY)
    add_rect(s, Inches(0.55), Inches(2.20), Inches(0.6), Inches(0.08), fill=ACCENT)
    add_text(
        s,
        Inches(0.55),
        Inches(2.40),
        Inches(12),
        Inches(0.5),
        "PE DOCUMENT INTELLIGENCE",
        size=14,
        bold=True,
        color=ACCENT,
    )
    add_text(
        s,
        Inches(0.55),
        Inches(2.85),
        Inches(12),
        Inches(1.2),
        "Evaluation Framework",
        size=54,
        bold=True,
        color=WHITE,
    )
    add_text(
        s,
        Inches(0.55),
        Inches(4.05),
        Inches(12),
        Inches(0.6),
        "Grading every LLM touchpoint of the LangGraph pipeline,",
        size=20,
        color=WHITE,
    )
    add_text(
        s,
        Inches(0.55),
        Inches(4.40),
        Inches(12),
        Inches(0.6),
        "the RAG layer, and the data agent.",
        size=20,
        color=WHITE,
    )
    add_text(
        s,
        Inches(0.55),
        Inches(6.40),
        Inches(12),
        Inches(0.4),
        "Backend: backend/evals  ·  Tests: backend/tests/evals  ·  Migration: alembic 004",
        size=11,
        color=ACCENT,
    )
    add_text(
        s,
        Inches(0.55),
        Inches(6.75),
        Inches(12),
        Inches(0.4),
        "Stack: Python · LangGraph · LangSmith · Postgres · React",
        size=11,
        color=WHITE,
    )


def slide_why(prs, page):
    s = blank(prs)
    header_bar(s, "Why a dedicated eval framework", "Motivation")
    cards = [
        (
            "Eight LLM surfaces, one quality contract",
            [
                "Classifier, extractor, judge, summarizer.",
                "RAG retriever + agentic ReAct.",
                "NL→SQL data agent, full pipeline graph.",
                "Each one needs its own definition of correct.",
            ],
            ACCENT,
        ),
        (
            "Catch silent regressions",
            [
                "Model upgrades change accuracy and calibration.",
                "Prompt edits can break refusal behaviour.",
                "Confidence drift goes unnoticed without ECE.",
            ],
            ORANGE,
        ),
        (
            "Close the dogfood loop",
            [
                "Every UI correction lands in long-term memory.",
                "Harvest job replays them as regression tests.",
                "New corrections become new tests, automatically.",
            ],
            GREEN,
        ),
        (
            "Trust through provenance",
            [
                "Every run stores model, judge model, git SHA.",
                "Per-example prediction + expected + score.",
                "Trends per (stage, evaluator) over time.",
            ],
            PURPLE,
        ),
    ]
    x0, y0 = Inches(0.55), Inches(1.55)
    cw, ch, gap = Inches(6.10), Inches(2.55), Inches(0.20)
    for i, (t, lines, c) in enumerate(cards):
        col, row = i % 2, i // 2
        card(
            s, x0 + (cw + gap) * col, y0 + (ch + gap) * row, cw, ch, t, lines, accent=c
        )
    footer(s, page)


def slide_overview(prs, page):
    s = blank(prs)
    header_bar(s, "Architecture at a glance", "Overview")
    y, h = Inches(1.7), Inches(0.85)
    boxes = [
        ("Datasets", "JSONL goldens\nper stage", ACCENT),
        ("Runner", "Loads, calls\nproduction LLM", PURPLE),
        ("Evaluators", "Metric · Judge\nRubric · Trajectory", GREEN),
        ("Persistence", "eval_runs +\neval_results (PG)", ORANGE),
        ("Dashboard", "/evals scorecards\n+ trends", RED),
    ]
    n = len(boxes)
    bw, gap = Inches(2.10), Inches(0.15)
    total_w = bw * n + gap * (n - 1)
    x0 = (SLIDE_W - total_w) / 2
    for i, (t, sub, c) in enumerate(boxes):
        x = x0 + (bw + gap) * i
        add_rect(s, x, y, bw, h, fill=WHITE, line=BORDER)
        add_rect(s, x, y, bw, Inches(0.10), fill=c)
        add_text(
            s,
            x,
            y + Inches(0.18),
            bw,
            Inches(0.32),
            t,
            size=14,
            bold=True,
            color=NAVY,
            align=PP_ALIGN.CENTER,
        )
        add_text(
            s,
            x,
            y + Inches(0.50),
            bw,
            Inches(0.42),
            sub,
            size=10,
            color=SUBTLE,
            align=PP_ALIGN.CENTER,
        )
        if i < n - 1:
            make_arrow(
                s,
                x + bw + Inches(0.01),
                y + Inches(0.32),
                gap - Inches(0.02),
                Inches(0.20),
            )

    add_text(
        s,
        Inches(0.55),
        Inches(3.10),
        Inches(12),
        Inches(0.4),
        "Side channels",
        size=14,
        bold=True,
        color=NAVY,
    )
    side = [
        ("LangSmith", "Datasets synced as pe-doc-intel/<stage>; experiments + traces."),
        (
            "Long-term memory → regression set",
            "harvest-regressions reads classification_corrections / extraction_corrections.",
        ),
        (
            "Phoenix (optional)",
            "OTLP traces to localhost:6006 for live judge debugging.",
        ),
    ]
    yy = Inches(3.55)
    for t, d in side:
        add_rect(s, Inches(0.55), yy, Inches(0.20), Inches(0.45), fill=ACCENT)
        add_text(
            s,
            Inches(0.85),
            yy,
            Inches(4.0),
            Inches(0.45),
            t,
            size=12,
            bold=True,
            color=NAVY,
            anchor=MSO_ANCHOR.MIDDLE,
        )
        add_text(
            s,
            Inches(4.85),
            yy,
            Inches(8),
            Inches(0.45),
            d,
            size=11,
            color=INK,
            anchor=MSO_ANCHOR.MIDDLE,
        )
        yy += Inches(0.55)
    footer(s, page)


def slide_surfaces(prs, page):
    s = blank(prs)
    header_bar(s, "Eight surfaces, one scoring contract", "Scope")
    rows = [
        ("Stage", "Production callable", "Why it needs evals"),
        (
            "classification",
            "classify_document()",
            "Wrong category → wrong extraction schema.",
        ),
        ("extraction", "extract_fields()", "Field accuracy + verbatim provenance."),
        (
            "judge (meta)",
            "src/graph_nodes/judge",
            "Confidence must correlate with correctness.",
        ),
        ("summarize", "summarize_document()", "Faithfulness + PE-checklist coverage."),
        ("rag", "RAGService.query()", "Retrieval IR metrics + answer faithfulness."),
        (
            "agentic_rag",
            "agentic_rag_query()",
            "Tool-call trajectory quality, not just answer.",
        ),
        ("sql", "run_analytics_query()", "NL→SQL safety + intent + chart shape."),
        (
            "pipeline",
            "build_pipeline().ainvoke",
            "Stage reachability + review-gate firing.",
        ),
    ]
    three_col_table(
        s,
        Inches(0.55),
        Inches(1.55),
        Inches(12.20),
        Inches(5.10),
        rows,
        ratios=(0.18, 0.30, 0.52),
    )
    add_text(
        s,
        Inches(0.55),
        Inches(6.75),
        Inches(12),
        Inches(0.30),
        "Every evaluator returns the same shape: { key, score, comment } — "
        "that uniformity is what lets the runner aggregate, persist, and chart anything.",
        size=10,
        color=SUBTLE,
    )
    footer(s, page)


def slide_layers(prs, page):
    s = blank(prs)
    header_bar(s, "Four evaluator layers", "Taxonomy")
    quads = [
        (
            "Metric-based",
            "Deterministic · cheap · CI-safe",
            [
                "exact match, numeric tolerance",
                "Recall@K, MRR, nDCG@K",
                "ECE (confidence calibration)",
                "source-text substring check",
                "PE-checklist coverage",
            ],
            ACCENT,
        ),
        (
            "LLM-as-judge",
            "Pydantic-structured · single criterion",
            [
                "summary + RAG faithfulness",
                "answer / context relevance",
                "extraction source fidelity (3-way)",
                "judge-meta calibration",
                "RAGAS triad (optional)",
            ],
            PURPLE,
        ),
        (
            "Rubric-based",
            "YAML, multi-criterion, weighted",
            [
                "extraction (4 criteria)",
                "summary (5 criteria)",
                "sql (5 criteria)",
                "agent_trajectory (4 criteria)",
                "auditable per-criterion reasoning",
            ],
            ORANGE,
        ),
        (
            "Trajectory",
            "Tool-call sequence quality",
            [
                "subset (required tools called)",
                "partial-order pairs respected",
                "no-unnecessary-calls (call budget)",
                "tool input quality (LLM judge)",
                "agent trajectory rubric",
            ],
            GREEN,
        ),
    ]
    x0, y0 = Inches(0.55), Inches(1.55)
    cw, ch, gap = Inches(6.10), Inches(2.65), Inches(0.20)
    for i, (t, sub, lines, c) in enumerate(quads):
        col, row = i % 2, i // 2
        x = x0 + (cw + gap) * col
        y = y0 + (ch + gap) * row
        add_rect(s, x, y, cw, ch, fill=WHITE, line=BORDER)
        add_rect(s, x, y, Inches(0.08), ch, fill=c)
        add_text(
            s,
            x + Inches(0.25),
            y + Inches(0.10),
            cw - Inches(0.35),
            Inches(0.40),
            t,
            size=15,
            bold=True,
            color=NAVY,
        )
        add_text(
            s,
            x + Inches(0.25),
            y + Inches(0.45),
            cw - Inches(0.35),
            Inches(0.30),
            sub,
            size=10,
            color=SUBTLE,
        )
        add_bullets(
            s,
            x + Inches(0.25),
            y + Inches(0.80),
            cw - Inches(0.35),
            ch - Inches(0.90),
            lines,
            size=11,
        )
    footer(s, page)
