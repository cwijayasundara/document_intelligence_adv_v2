"""Summary golden-dataset synthesizer.

Per source document we ask the judge to write a faithful PE-style reference
summary plus a `pe_checklist` (dict of fact name -> verbatim value) covering
the load-bearing terms (fund_name, fees, term, etc). The verifier confirms
every checklist value is present in the document and that no claim in the
summary goes beyond the source text.

Output schema matches `evals/datasets/summary_golden.jsonl` so the existing
`runners/run_summary.py` consumes it unchanged.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator, ClassVar

from pydantic import BaseModel, Field

from ..base import GoldenRow, ParsedDoc, SynthCtx, Synthesizer
from ..judge import judge_call

logger = logging.getLogger(__name__)


_GEN_SYSTEM_BASE = """\
You are a domain expert writing a *gold-standard* reference summary of a
single document{domain_clause} for an evaluation dataset. The summary will be
used to grade an automated summarizer, so it must be faithful and concise.

Write:
- `reference_summary`: 2-7 tight sentences (5-7 for long/full documents, 2-3
  for short fragments). Cover the load-bearing facts that the document
  actually states (key entities, identifiers, amounts, dates, decisions,
  outcomes — whatever is salient for THIS document type). Never invent or
  infer. No marketing fluff, no future tense, no boilerplate.
- `pe_checklist`: a list of {{key, value}} items where `key` is a stable fact
  name (snake_case) and `value` is a short verbatim token from the document.
  Pick the load-bearing facts; values must appear in the source text.
  (Field name kept as `pe_checklist` for backward compatibility with the
  grading runner; the keys themselves should fit THIS document, not any
  particular vertical.)
- `expected_min_topics`: integer 2-6, the floor on how many distinct topics
  a faithful summary must cover. Lower for short fragments; higher for full
  documents.
- `tags`: 1-3 short labels describing the doc shape (e.g. "short", "partial",
  "full", or any vertical-specific labels that make sense for the corpus).

Skip any field you can't ground. If the document is too short / boilerplate
to summarize at all, set `skip=true` and leave the other fields empty.
"""


def _gen_system(domain_hint: str | None) -> str:
    clause = f" of {domain_hint}" if domain_hint else ""
    return _GEN_SYSTEM_BASE.format(domain_clause=clause)


class _ChecklistItem(BaseModel):
    key: str
    value: str


class _GenOutput(BaseModel):
    skip: bool = Field(default=False)
    reference_summary: str = Field(default="")
    pe_checklist: list[_ChecklistItem] = Field(default_factory=list)
    expected_min_topics: int = Field(default=2, ge=1, le=10)
    tags: list[str] = Field(default_factory=list)


_VERIFY_SYSTEM = """\
You are a strict verifier of a candidate reference summary. You will be shown
the source document, the candidate `reference_summary`, and the candidate
`pe_checklist`. Decide:

- `summary_entailed`: True iff every claim in the reference summary is
  supported by the document (no outside knowledge, no invented numbers/names).
- `checklist_grounded`: True iff EVERY value in `pe_checklist` appears as a
  substring of the document (whitespace-insensitive, case-insensitive). The
  value does NOT need to be a standalone token — "Delaware" is grounded if
  the source contains "State of Delaware" or "Delaware limited partnership".
  Numbers/percentages must match exactly (e.g. "2.0%" is grounded only if
  "2.0%" or "2%" appears).
- `summary_concise`: True iff the summary is 2-7 sentences and avoids
  marketing/boilerplate filler.
- `reasoning`: one sentence.
"""


class _VerifyOutput(BaseModel):
    summary_entailed: bool
    checklist_grounded: bool
    summary_concise: bool
    reasoning: str = ""


def _format_gen_user(doc: ParsedDoc) -> str:
    body = doc.markdown[:24_000]
    return (
        f"# Document\n"
        f"doc_id: {doc.doc_id}\n"
        f"path: {doc.source_path.name}\n\n"
        f"# Document text\n```\n{body}\n```\n"
    )


def _format_verify_user(doc: ParsedDoc, gen: _GenOutput) -> str:
    body = doc.markdown[:24_000]
    return (
        f"# Document text\n```\n{body}\n```\n\n"
        f"# Candidate\n"
        f"reference_summary: {gen.reference_summary}\n"
        f"pe_checklist: {gen.pe_checklist}\n"
        f"expected_min_topics: {gen.expected_min_topics}\n"
    )


def _normalize_ws(s: str) -> str:
    return " ".join(s.split()).lower()


class SummarySynthesizer(Synthesizer):
    kind: ClassVar[str] = "summary"
    output_file: ClassVar[str] = "summary_golden.jsonl"
    required_fields: ClassVar[set[str]] = set()

    async def synthesize(
        self,
        docs: list[ParsedDoc],
        *,
        n: int,
        ctx: SynthCtx,
    ) -> AsyncIterator[GoldenRow]:
        gen_system = _gen_system(ctx.domain_hint)
        emitted = 0
        for doc in docs:
            if emitted >= n:
                break
            try:
                gen = await judge_call(
                    ctx=ctx,
                    system=gen_system,
                    user=_format_gen_user(doc),
                    schema=_GenOutput,
                    purpose="summary.generate",
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("summary.generate failed (doc=%s): %s", doc.doc_id, exc)
                continue

            if gen.skip or not gen.reference_summary or not gen.pe_checklist:
                continue

            normalized_doc = _normalize_ws(doc.markdown)
            checklist: dict[str, str] = {}
            for item in gen.pe_checklist:
                if not (item.key and item.value) or item.key in checklist:
                    continue
                if _normalize_ws(item.value) not in normalized_doc:
                    logger.debug(
                        "summary: dropping ungrounded item %s=%r", item.key, item.value
                    )
                    continue
                checklist[item.key] = item.value
            if len(checklist) < 3:
                logger.debug(
                    "summary: too few grounded items (%d) for %s", len(checklist), doc.doc_id
                )
                continue

            try:
                verdict = await judge_call(
                    ctx=ctx,
                    system=_VERIFY_SYSTEM,
                    user=_format_verify_user(doc, gen),
                    schema=_VerifyOutput,
                    purpose="summary.verify",
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("summary.verify failed: %s", exc)
                continue

            if not (verdict.summary_entailed and verdict.checklist_grounded and verdict.summary_concise):
                logger.debug("summary.verify rejected %s: %s", doc.doc_id, verdict.reasoning)
                continue

            row: GoldenRow = {
                "id": f"sum_synth_{doc.doc_id}",
                "doc_id": doc.doc_id,
                "parsed_path": doc.parsed_path_str,
                "reference_summary": gen.reference_summary.strip(),
                "pe_checklist": checklist,
                "expected_min_topics": int(gen.expected_min_topics),
                "tags": list({*gen.tags, *ctx.tags, "synth"}),
                "synth": {
                    "judge_model": ctx.judge_model,
                    "source_doc_id": doc.doc_id,
                    "seed": ctx.seed,
                    "verifier_reasoning": verdict.reasoning,
                },
            }
            emitted += 1
            yield row

    def validate(self, row: GoldenRow) -> None:
        super().validate(row)
        for key in ("doc_id", "reference_summary", "pe_checklist"):
            if not row.get(key):
                raise ValueError(f"summary row missing/empty field: {key}")
        if not isinstance(row["pe_checklist"], dict):
            raise ValueError("pe_checklist must be a dict")
        if not row.get("parsed_path") and not row.get("inline_content"):
            raise ValueError("summary row needs parsed_path or inline_content")
