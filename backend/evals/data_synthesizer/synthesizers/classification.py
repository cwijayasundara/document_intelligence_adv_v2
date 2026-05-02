"""Classification golden-dataset synthesizer.

Per source document we ask the judge to pick exactly one category from a
caller-supplied list, with a confidence score. A separate verifier judge
re-reads the same document text and re-picks the category; we only emit a
row when both passes agree.

Categories come from `ctx.categories` (CLI: `--categories`). Each entry may
include a description after a colon, e.g. "Invoice: AR document with line
items, Receipt: payment confirmation". This synthesizer does NOT hardcode a
vertical.

Output schema matches `evals/datasets/classification_golden.jsonl` so the
existing `runners/run_classification.py` consumes it unchanged.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator, ClassVar

from pydantic import BaseModel, Field

from ..base import GoldenRow, ParsedDoc, SynthCtx, Synthesizer
from ..judge import judge_call

logger = logging.getLogger(__name__)


_GEN_SYSTEM_BASE = """\
You are classifying a document into exactly ONE of the provided categories{domain_clause}.
Pick the single best fit; if nothing fits well, pick the catch-all category
named "Other" (case-insensitive) when one is provided.

Provide:
- `category`: exactly one of the provided category names (no paraphrasing).
- `confidence`: integer 0–100 reflecting how clearly the document fits.
  - >=80 only when the category signals are explicit and unambiguous.
  - 50–79 when signals exist but are partial, fragmentary, or noisy.
  - <50 when the document is too short or noisy to confidently classify.
- `evidence_substrings`: 1–3 verbatim short quotes from the document
  (≤120 chars each) that justify the category. Whitespace differences allowed,
  but the tokens must be present in the source.
- `reasoning`: one sentence.
"""


def _split_category_entry(entry: str) -> tuple[str, str | None]:
    """Parse "Name" or "Name: description" into (name, description)."""
    if ":" in entry:
        name, _, desc = entry.partition(":")
        return name.strip(), desc.strip() or None
    return entry.strip(), None


def _format_categories_block(entries: list[str]) -> str:
    lines: list[str] = []
    for entry in entries:
        name, desc = _split_category_entry(entry)
        if desc:
            lines.append(f"- {name} — {desc}")
        else:
            lines.append(f"- {name}")
    return "\n".join(lines)


def _category_names(entries: list[str]) -> list[str]:
    return [_split_category_entry(e)[0] for e in entries]


def _gen_system(domain_hint: str | None) -> str:
    clause = f" of {domain_hint}" if domain_hint else ""
    return _GEN_SYSTEM_BASE.format(domain_clause=clause)


class _GenOutput(BaseModel):
    category: str
    confidence: int = Field(ge=0, le=100)
    evidence_substrings: list[str] = Field(default_factory=list)
    reasoning: str = ""


_VERIFY_SYSTEM = """\
You are a strict second-pass verifier. Re-read the document and decide:

- `category`: which of the provided categories best fits this document.
  Return exactly one of the provided category names.
- `evidence_present`: True iff every item in `claimed_evidence` appears as a
  substring of the document (whitespace-insensitive, case-insensitive).
- `confidence_reasonable`: True iff the claimed confidence score is
  consistent with the category strength of the document (e.g. don't accept
  >80 confidence on a 5-line excerpt).

The row will be kept only if your `category` matches the candidate's
`category`, evidence is present, and confidence is reasonable.
"""


class _VerifyOutput(BaseModel):
    category: str
    evidence_present: bool
    confidence_reasonable: bool
    reasoning: str = ""


def _format_gen_user(doc: ParsedDoc, categories_block: str) -> str:
    body = doc.markdown[:24_000]
    return (
        f"# Document\n"
        f"doc_id: {doc.doc_id}\n"
        f"path: {doc.source_path.name}\n\n"
        f"# Categories (pick exactly one)\n{categories_block}\n\n"
        f"# Document text\n```\n{body}\n```\n"
    )


def _format_verify_user(doc: ParsedDoc, gen: _GenOutput, categories_block: str) -> str:
    body = doc.markdown[:24_000]
    return (
        f"# Document text\n```\n{body}\n```\n\n"
        f"# Categories\n{categories_block}\n\n"
        f"# Candidate\n"
        f"category: {gen.category}\n"
        f"confidence: {gen.confidence}\n"
        f"claimed_evidence: {gen.evidence_substrings}\n"
    )


def _normalize_ws(s: str) -> str:
    return " ".join(s.split()).lower()


class ClassificationSynthesizer(Synthesizer):
    kind: ClassVar[str] = "classification"
    output_file: ClassVar[str] = "classification_golden.jsonl"
    required_fields: ClassVar[set[str]] = set()

    async def synthesize(
        self,
        docs: list[ParsedDoc],
        *,
        n: int,
        ctx: SynthCtx,
    ) -> AsyncIterator[GoldenRow]:
        if not ctx.categories:
            raise ValueError(
                "kind=classification requires --categories "
                "(comma-separated list, optionally with 'Name: description')"
            )

        category_names = _category_names(ctx.categories)
        category_set = set(category_names)
        block = _format_categories_block(ctx.categories)
        gen_system = _gen_system(ctx.domain_hint)

        emitted = 0
        for doc in docs:
            if emitted >= n:
                break
            try:
                gen = await judge_call(
                    ctx=ctx,
                    system=gen_system,
                    user=_format_gen_user(doc, block),
                    schema=_GenOutput,
                    purpose="classification.generate",
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("classification.generate failed (doc=%s): %s", doc.doc_id, exc)
                continue

            if gen.category not in category_set:
                logger.debug(
                    "classification: judge picked unknown category %r (allowed=%s) for %s",
                    gen.category,
                    sorted(category_set),
                    doc.doc_id,
                )
                continue

            normalized_doc = _normalize_ws(doc.markdown)
            if any(_normalize_ws(s) not in normalized_doc for s in gen.evidence_substrings):
                logger.debug("classification: evidence not in source for %s", doc.doc_id)
                continue

            try:
                verdict = await judge_call(
                    ctx=ctx,
                    system=_VERIFY_SYSTEM,
                    user=_format_verify_user(doc, gen, block),
                    schema=_VerifyOutput,
                    purpose="classification.verify",
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("classification.verify failed: %s", exc)
                continue

            if verdict.category != gen.category:
                logger.debug(
                    "classification.verify disagreed (gen=%s verify=%s) for %s",
                    gen.category,
                    verdict.category,
                    doc.doc_id,
                )
                continue
            if not (verdict.evidence_present and verdict.confidence_reasonable):
                logger.debug("classification.verify rejected %s: %s", doc.doc_id, verdict.reasoning)
                continue

            confidence_floor = max(40, min(95, int(gen.confidence) - 10))
            row: GoldenRow = {
                "id": f"cls_synth_{doc.doc_id}",
                "tags": list({"synth", *ctx.tags}),
                "file_name": f"{doc.source_path.stem}.pdf",
                "parsed_path": doc.parsed_path_str,
                "expected_category": gen.category,
                "expected_min_confidence": confidence_floor,
                "notes": (gen.reasoning or "").strip(),
                "synth": {
                    "judge_model": ctx.judge_model,
                    "source_doc_id": doc.doc_id,
                    "seed": ctx.seed,
                    "domain_hint": ctx.domain_hint,
                    "categories": list(category_names),
                    "generator_confidence": gen.confidence,
                    "evidence_substrings": gen.evidence_substrings,
                    "verifier_reasoning": verdict.reasoning,
                },
            }
            emitted += 1
            yield row

    def validate(self, row: GoldenRow) -> None:
        super().validate(row)
        for key in ("file_name", "expected_category"):
            if not row.get(key):
                raise ValueError(f"classification row missing/empty field: {key}")
        if not row.get("parsed_path") and not row.get("inline_content"):
            raise ValueError("classification row needs parsed_path or inline_content")
