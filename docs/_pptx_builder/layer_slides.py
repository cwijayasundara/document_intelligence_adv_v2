"""Slides 6–10: per-layer deep dives (metric, judge, rubric, trajectory, sql)."""

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
    three_col_table,
    two_col_table,
)
from .theme import INK, MUTED_BG, NAVY, SUBTLE


def slide_metric(prs, page):
    s = blank(prs)
    header_bar(s, "Metric-based — fast, deterministic, CI-safe", "Layer 1 of 4")
    rows = [
        ("Metric", "Stage", "What it scores"),
        ("classification_accuracy", "classification", "Case-insensitive name match."),
        (
            "calibration_ece",
            "classification",
            "Expected Calibration Error across confidence deciles. Lower is better.",
        ),
        (
            "extraction_exact_match",
            "extraction",
            "Loose-normalised match; honours expected_accepted_values + expected_empty.",
        ),
        (
            "extraction_numeric_tolerance",
            "extraction",
            "Absolute-tolerance numeric compare for fees / rates / periods.",
        ),
        (
            "extraction_source_substring",
            "extraction",
            "Predicted source_text is a substring of the doc — catches hallucinated provenance.",
        ),
        (
            "retrieval_recall@5 / MRR / nDCG@10",
            "rag",
            "Standard IR over expected_relevant_chunk_substrings.",
        ),
        (
            "rag_answer_contains / citation_count",
            "rag",
            "Required substrings (all_of | any_of); citation count window.",
        ),
        (
            "summary_pe_checklist_coverage",
            "summary",
            "Fraction of PE attributes (fund name, fee, carry, …) that appear in the summary.",
        ),
    ]
    three_col_table(
        s,
        Inches(0.55),
        Inches(1.55),
        Inches(12.20),
        Inches(5.30),
        rows,
        ratios=(0.30, 0.18, 0.52),
    )
    add_text(
        s,
        Inches(0.55),
        Inches(6.95),
        Inches(12),
        Inches(0.3),
        "All metrics here run with no API key — the same code path runs in CI and locally.",
        size=10,
        color=SUBTLE,
    )
    footer(s, page)


def slide_judge(prs, page):
    s = blank(prs)
    header_bar(s, "LLM-as-judge — structured, model-graded", "Layer 2 of 4")
    rows = [
        ("Judge schema", "Returns", "Used for"),
        (
            "FaithfulnessJudgement",
            "faithful · score · unsupported_claims",
            "summary_faithfulness, rag_answer_faithfulness",
        ),
        (
            "AnswerRelevanceJudgement",
            "on_topic · score · reasoning",
            "rag_answer_relevance",
        ),
        (
            "ContextRelevanceJudgement",
            "per_chunk_scores · mean",
            "rag_context_relevance",
        ),
        (
            "BinaryJudgement",
            "passed · score · reasoning",
            "extraction_source_fidelity, sql_intent_match, tool_input_quality",
        ),
        (
            "JudgeMetaJudgement",
            "calibrated · score · reasoning",
            "judge_meta_calibration (grades the production Judge)",
        ),
        (
            "RAGAS triad (optional)",
            "faithfulness + relevancy + precision",
            "ragas_triad — composite RAG score",
        ),
    ]
    three_col_table(
        s,
        Inches(0.55),
        Inches(1.55),
        Inches(12.20),
        Inches(4.20),
        rows,
        ratios=(0.28, 0.32, 0.40),
    )
    add_rect(s, Inches(0.55), Inches(5.95), Inches(12.20), Inches(1.0), fill=MUTED_BG)
    add_text(
        s,
        Inches(0.75),
        Inches(6.05),
        Inches(11.8),
        Inches(0.40),
        "Judge model selection",
        size=12,
        bold=True,
        color=NAVY,
    )
    add_text(
        s,
        Inches(0.75),
        Inches(6.40),
        Inches(11.8),
        Inches(0.55),
        "Default: one tier above production (gpt-5.2 → gpt-5.3, gpt-5.1 → gpt-5.2). "
        "Override via EVAL_JUDGE_MODEL. Temperature pinned to 0.",
        size=11,
        color=INK,
    )
    footer(s, page)


def slide_rubric(prs, page):
    s = blank(prs)
    header_bar(s, "Rubrics — multi-criterion, YAML-defined", "Layer 3 of 4")
    code = """name: extraction
scale: [1, 5]
criteria:
  - id: verbatim_quote
    weight: 0.35
    anchors:
      "1": "Source text is fabricated."
      "5": "Exact verbatim quote with context."
  - id: value_format        { weight: 0.25 }
  - id: unit_correctness    { weight: 0.20 }
  - id: completeness        { weight: 0.20 }
"""
    code_block(s, Inches(0.55), Inches(1.55), Inches(6.50), Inches(3.40), code, size=10)

    add_text(
        s,
        Inches(7.30),
        Inches(1.55),
        Inches(5.50),
        Inches(0.40),
        "Aggregation",
        size=15,
        bold=True,
        color=NAVY,
    )
    add_bullets(
        s,
        Inches(7.30),
        Inches(2.00),
        Inches(5.50),
        Inches(3.0),
        [
            "Single judge call returns scores per criterion.",
            "Weighted sum, normalised to [0, 1].",
            "Raw composite kept on the rubric scale (1..5).",
            "Missing criterion → floor; out-of-range → clipped.",
            "Per-criterion reasoning preserved for auditing.",
        ],
        size=12,
    )

    add_text(
        s,
        Inches(0.55),
        Inches(5.20),
        Inches(12),
        Inches(0.40),
        "Shipped rubrics",
        size=15,
        bold=True,
        color=NAVY,
    )
    rows = [
        ("Rubric", "Top-weighted criteria"),
        (
            "extraction",
            "verbatim_quote 0.35 · value_format 0.25 · unit_correctness 0.20",
        ),
        ("summary", "pe_attribute_coverage 0.35 · faithfulness 0.35"),
        (
            "sql",
            "sql_intent_match 0.35 · chart_axes_sensible 0.20 · chart_type_appropriate 0.20",
        ),
        ("agent_trajectory", "tool_selection 0.30 · query_reformulation_quality 0.25"),
    ]
    two_col_table(
        s,
        Inches(0.55),
        Inches(5.65),
        Inches(12.20),
        Inches(1.40),
        rows,
        col1_w_ratio=0.22,
    )
    footer(s, page)


def slide_trajectory(prs, page):
    s = blank(prs)
    header_bar(s, "Trajectory — agentic RAG tool-call grading", "Layer 4 of 4")
    add_text(
        s,
        Inches(0.55),
        Inches(1.55),
        Inches(6.20),
        Inches(0.4),
        "Production trajectory shape",
        size=14,
        bold=True,
        color=NAVY,
    )
    code = """{
  "answer": "...",
  "trajectory": [
    {"type": "tool_call",
     "name": "search_documents", "args": {...}},
    {"type": "tool_result", ...},
    {"type": "tool_call",
     "name": "lookup_extractions", ...}
  ]
}"""
    code_block(s, Inches(0.55), Inches(2.00), Inches(6.20), Inches(2.60), code, size=10)

    add_text(
        s,
        Inches(7.05),
        Inches(1.55),
        Inches(5.70),
        Inches(0.4),
        "Evaluators",
        size=14,
        bold=True,
        color=NAVY,
    )
    add_bullets(
        s,
        Inches(7.05),
        Inches(2.00),
        Inches(5.70),
        Inches(2.60),
        [
            "trajectory_subset — required tools called.",
            "trajectory_order — partial-order pairs respected.",
            "no_unnecessary_calls — call-budget penalty.",
            "tool_input_quality — LLM-graded args.",
            "rubric_agent_trajectory — composite.",
        ],
        size=12,
    )

    add_rect(s, Inches(0.55), Inches(4.85), Inches(12.20), Inches(1.95), fill=MUTED_BG)
    add_text(
        s,
        Inches(0.75),
        Inches(4.95),
        Inches(11.8),
        Inches(0.4),
        "Why grade trajectory, not just the answer?",
        size=14,
        bold=True,
        color=NAVY,
    )
    add_bullets(
        s,
        Inches(0.75),
        Inches(5.35),
        Inches(11.8),
        Inches(1.40),
        [
            "Correct answer + 12 tool calls is a worse agent than correct answer + 2.",
            "Catches cost regressions: ReAct loops invisible to answer-only metrics.",
            "Catches reasoning regressions: wrong tool, right answer = lucky.",
        ],
        size=12,
    )
    footer(s, page)


def slide_sql(prs, page):
    s = blank(prs)
    header_bar(s, "SQL safety, intent, and execution-match", "Data agent")
    add_text(
        s,
        Inches(0.55),
        Inches(1.55),
        Inches(12),
        Inches(0.4),
        "AST-based safety (sqlglot) — not regex",
        size=14,
        bold=True,
        color=NAVY,
    )
    rows = [
        ("Evaluator", "What it does"),
        ("sql_validity", "Single, parseable Postgres statement."),
        (
            "sql_safety",
            "Walks AST; rejects Insert/Update/Delete/Drop/Create/Alter/Truncate/Merge/Grant/Revoke.",
        ),
        (
            "sql_rejected_as_expected",
            "For negative cases — confirms refusal (empty SQL + non-empty error/explanation).",
        ),
        (
            "sql_contains_keywords",
            "Soft signal: required keywords present in generated SQL.",
        ),
        ("chart_shape", "Predicted chart_type ∈ expected_accepted_chart_types."),
        (
            "sql_exec_match",
            "Executes both reference + predicted SQL inside a rolled-back transaction; "
            "row-set equality with Jaccard fallback.",
        ),
        (
            "sql_intent_match (judge)",
            "Would the SQL, if executed, answer the user's question?",
        ),
        (
            "rubric_sql",
            "5-criterion composite — intent · parsimony · chart type · axes · explanation.",
        ),
    ]
    two_col_table(
        s,
        Inches(0.55),
        Inches(2.05),
        Inches(12.20),
        Inches(4.80),
        rows,
        col1_w_ratio=0.30,
    )
    add_text(
        s,
        Inches(0.55),
        Inches(6.95),
        Inches(12),
        Inches(0.30),
        "Execution-match wraps everything in a transaction that always rolls back — "
        "read-only by construction.",
        size=10,
        color=SUBTLE,
    )
    footer(s, page)
