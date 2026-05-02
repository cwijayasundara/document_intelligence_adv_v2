"""SQL (text-to-SQL) golden-dataset synthesizer.

Unlike the document-driven kinds, SQL is *schema*-driven: the production data
agent answers analytics questions over a fixed PE document-intel schema. We
hand the judge a frozen, annotated description of that schema and ask it to
produce realistic NL/SQL pairs.

Each generated row is gated by:
  1. Local SELECT-only / SQL-validity checks (cheap).
  2. A verifier judge that re-checks SQL safety and intent against the schema.

Negative scenarios (DDL/DML rejection, RAG-routing rejection) are emitted
deterministically from a fixed list — they exercise refusal paths and have
nothing to learn from a judge.

Output schema matches `evals/datasets/sql_golden.jsonl` so the existing
`runners/run_sql.py` consumes it unchanged.
"""

from __future__ import annotations

import logging
import re
from typing import AsyncIterator, ClassVar

from pydantic import BaseModel, Field

from ..base import GoldenRow, ParsedDoc, SynthCtx, Synthesizer
from ..judge import judge_call
from ._sql_fixtures import (
    INTENT_HINTS,
    NEGATIVE_ROWS,
    SCHEMA_DESCRIPTION,
    VALID_CHART_TYPES,
    is_select_only,
)

logger = logging.getLogger(__name__)


_GEN_SYSTEM = """\
You are creating realistic NL -> SQL evaluation pairs for an analytics agent
operating on a Postgres database. The agent is SELECT-only.

For ONE example, return:
- `question`: a natural-language analytics question an internal user would ask.
  Concrete, single-intent, under 25 words.
- `reference_sql`: a single Postgres SELECT statement that answers the question
  using ONLY tables/columns in the provided schema. No DDL/DML, no semicolons
  beyond a single trailing semicolon. Use lowercase keywords or uppercase —
  pick one and stay consistent. JOINs are fine. Use aliases for clarity.
- `expected_sql_contains`: 2-5 case-insensitive tokens any correct SQL must
  contain (e.g. ["SELECT", "status", "COUNT", "GROUP BY"]). Pick the
  load-bearing keywords/identifiers, NOT generic words.
- `expected_chart_type`: one of "bar", "line", "pie", "table". Use "line" for
  time-series, "pie"/"bar" for categorical breakdowns, "table" for listings
  or single scalar.
- `expected_columns`: the column names (or aliases) the SQL projects, in order.
  Empty list is acceptable when the SQL returns a single scalar.
- `expected_min_rows`: integer >=0 — the minimum number of rows a correct
  answer must return on a non-empty database. Use 0 when filters can
  legitimately return zero rows.
- `tags`: 1-3 short labels (e.g. ["aggregation", "categories"]).

If you can't ground a clean SELECT in the schema, set `skip=true`.
"""


class _GenOutput(BaseModel):
    skip: bool = Field(default=False)
    question: str = Field(default="")
    reference_sql: str = Field(default="")
    expected_sql_contains: list[str] = Field(default_factory=list)
    expected_chart_type: str = Field(default="table")
    expected_columns: list[str] = Field(default_factory=list)
    expected_min_rows: int = Field(default=0, ge=0)
    tags: list[str] = Field(default_factory=list)


_VERIFY_SYSTEM = """\
You are verifying a candidate (question, SQL, contains-keywords, chart) tuple
against a frozen Postgres schema.

Decide:
- `sql_select_only`: True iff the SQL is a single SELECT (or WITH ... SELECT)
  statement with no DDL/DML/transaction control.
- `references_real_columns`: True iff every table/column the SQL references
  exists in the provided schema. Reject typos and hallucinated columns.
- `keywords_present`: True iff every token in `expected_sql_contains` appears
  (case-insensitive) in the reference SQL.
- `chart_type_reasonable`: True iff the chart type is sensible for the shape
  of the SQL output (line for timeseries, pie/bar for categorical
  distribution, table for listings/scalars).
- `reasoning`: one sentence.
"""


class _VerifyOutput(BaseModel):
    sql_select_only: bool
    references_real_columns: bool
    keywords_present: bool
    chart_type_reasonable: bool
    reasoning: str = ""


def _format_gen_user(intent_hint: str | None) -> str:
    hint = f"\nSuggested intent: {intent_hint}\n" if intent_hint else ""
    return f"# Schema\n{SCHEMA_DESCRIPTION}\n{hint}"


def _format_verify_user(gen: _GenOutput) -> str:
    return (
        f"# Schema\n{SCHEMA_DESCRIPTION}\n\n"
        f"# Candidate\n"
        f"question: {gen.question}\n"
        f"reference_sql: {gen.reference_sql}\n"
        f"expected_sql_contains: {gen.expected_sql_contains}\n"
        f"expected_chart_type: {gen.expected_chart_type}\n"
        f"expected_columns: {gen.expected_columns}\n"
    )


def _slug(text: str, fallback: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:48]
    return s or fallback


class SqlSynthesizer(Synthesizer):
    kind: ClassVar[str] = "sql"
    output_file: ClassVar[str] = "sql_golden.jsonl"
    required_fields: ClassVar[set[str]] = set()

    async def synthesize(
        self,
        docs: list[ParsedDoc],
        *,
        n: int,
        ctx: SynthCtx,
    ) -> AsyncIterator[GoldenRow]:
        # SQL synth is schema-driven; source docs aren't read. We still take
        # them to keep the CLI uniform.
        del docs

        # Always emit the negative refusal cases first — they're free and
        # essential coverage.
        for row in NEGATIVE_ROWS:
            yield dict(row)

        positives_target = max(0, n - len(NEGATIVE_ROWS))
        if positives_target == 0:
            return

        emitted = 0
        attempts = positives_target * 3  # oversample so verifier rejects don't starve us
        for i in range(attempts):
            if emitted >= positives_target:
                break
            intent = INTENT_HINTS[(ctx.seed + i) % len(INTENT_HINTS)]
            gen = await self._generate(ctx, intent)
            if gen is None:
                continue
            verdict = await self._verify(ctx, gen)
            if verdict is None:
                continue
            yield self._row_from(gen, intent=intent, verdict=verdict, ctx=ctx, idx=i)
            emitted += 1

    async def _generate(self, ctx: SynthCtx, intent: str) -> _GenOutput | None:
        try:
            gen = await judge_call(
                ctx=ctx,
                system=_GEN_SYSTEM,
                user=_format_gen_user(intent),
                schema=_GenOutput,
                purpose="sql.generate",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("sql.generate failed (intent=%s): %s", intent, exc)
            return None

        if gen.skip or not gen.question or not gen.reference_sql:
            return None
        if not is_select_only(gen.reference_sql):
            logger.debug("sql: not SELECT-only: %s", gen.reference_sql[:120])
            return None
        if gen.expected_chart_type not in VALID_CHART_TYPES:
            logger.debug("sql: invalid chart_type %r", gen.expected_chart_type)
            return None
        sql_lc = gen.reference_sql.lower()
        if any(tok.lower() not in sql_lc for tok in gen.expected_sql_contains):
            logger.debug("sql: expected_sql_contains tokens not all in reference_sql")
            return None
        return gen

    async def _verify(self, ctx: SynthCtx, gen: _GenOutput) -> _VerifyOutput | None:
        try:
            verdict = await judge_call(
                ctx=ctx,
                system=_VERIFY_SYSTEM,
                user=_format_verify_user(gen),
                schema=_VerifyOutput,
                purpose="sql.verify",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("sql.verify failed: %s", exc)
            return None
        all_ok = (
            verdict.sql_select_only
            and verdict.references_real_columns
            and verdict.keywords_present
            and verdict.chart_type_reasonable
        )
        if not all_ok:
            logger.debug("sql.verify rejected: %s", verdict.reasoning)
            return None
        return verdict

    def _row_from(
        self,
        gen: _GenOutput,
        *,
        intent: str,
        verdict: _VerifyOutput,
        ctx: SynthCtx,
        idx: int,
    ) -> GoldenRow:
        return {
            "id": f"sql_synth_{_slug(gen.question, fallback=f'q{idx}')}",
            "question": gen.question.strip(),
            "expected_sql_contains": gen.expected_sql_contains,
            "reference_sql": gen.reference_sql.strip(),
            "expected_min_rows": int(gen.expected_min_rows),
            "expected_chart_type": gen.expected_chart_type,
            "expected_columns": gen.expected_columns,
            "tags": list({*gen.tags, *ctx.tags, "synth"}),
            "synth": {
                "judge_model": ctx.judge_model,
                "intent_hint": intent,
                "seed": ctx.seed,
                "verifier_reasoning": verdict.reasoning,
            },
        }

    def validate(self, row: GoldenRow) -> None:
        super().validate(row)
        if not row.get("question"):
            raise ValueError("sql row missing 'question'")
        if row.get("expected_sql_rejected"):
            if not row.get("expected_error_contains"):
                raise ValueError("rejected sql row needs expected_error_contains")
            return
        for key in ("expected_sql_contains", "reference_sql", "expected_chart_type"):
            if not row.get(key):
                raise ValueError(f"sql row missing/empty field: {key}")
        if row["expected_chart_type"] not in VALID_CHART_TYPES:
            raise ValueError(f"unknown expected_chart_type: {row['expected_chart_type']}")
        if not is_select_only(row["reference_sql"]):
            raise ValueError("reference_sql is not SELECT-only")
