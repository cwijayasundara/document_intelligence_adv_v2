"""Extraction golden-dataset synthesizer.

Per source document we ask the judge to identify extractable fields the doc
clearly states, with verbatim source spans. The verifier re-checks each
(field, value, span) triple against the source text. Only triples that
verify get emitted.

Two modes:
- *Schema mode* — when `ctx.fields` is non-empty, the judge is asked to
  extract values for that exact list of fields (each entry: field_name +
  data_type). Use this when you want consistent fields across the corpus.
- *Discovery mode* — when `ctx.fields` is empty (default), the judge picks
  the salient extractable fields per document. Field names and data_types
  come from the model. Use this for any vertical without committing up
  front to a schema.

Output schema matches `evals/datasets/extraction_golden.jsonl` so the existing
`runners/run_extraction.py` consumes it unchanged.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator, ClassVar

from pydantic import BaseModel, Field

from ..base import GoldenRow, ParsedDoc, SynthCtx, Synthesizer
from ..judge import judge_call

logger = logging.getLogger(__name__)


# Allowed data types — kept tight so downstream evaluators can reason about
# the value shape without parsing free-form labels.
_ALLOWED_DATA_TYPES: set[str] = {
    "string",
    "number",
    "percentage",
    "currency",
    "date",
    "boolean",
    "enum",
}


_GEN_SYSTEM_BASE = """\
You are extracting structured fields from a document for a golden evaluation
dataset{domain_clause}.

{schema_clause}

For each field that is clearly stated in the document:
- Provide the value in a normalised form (percentages with %, currencies as
  written e.g. "USD 500,000,000" or "$500,000,000", dates verbatim, strings
  verbatim).
- Provide a `source_substring` — a short verbatim quote from the document
  (≤ 200 chars) that proves the value. The substring MUST appear in the doc
  character-for-character (whitespace-insensitive).
- Set `confidence` ∈ [0, 1] for how sure you are.

Skip any field that is not clearly stated. Do NOT guess. Prefer fewer,
high-confidence fields over many speculative ones.
"""


_DISCOVERY_SCHEMA_CLAUSE = (
    "There is NO predefined schema. Pick the salient extractable fields you\n"
    "see in the document yourself. Use snake_case for `field_name` (e.g.\n"
    "invoice_number, total_amount, patient_age). Set `data_type` to one of:\n"
    "string | number | percentage | currency | date | boolean | enum."
)


def _schema_clause(fields: list[dict[str, str]]) -> str:
    if not fields:
        return _DISCOVERY_SCHEMA_CLAUSE
    rows = "\n".join(f"  - {f['field_name']} ({f['data_type']})" for f in fields)
    return (
        "Extract values for the following fields ONLY. Do not invent new "
        "field names; skip any field that is not stated.\n\n"
        f"{rows}"
    )


def _gen_system(ctx: SynthCtx) -> str:
    domain = f" of {ctx.domain_hint}" if ctx.domain_hint else ""
    return _GEN_SYSTEM_BASE.format(
        domain_clause=domain,
        schema_clause=_schema_clause(ctx.fields),
    )


class _ExtractedFieldOut(BaseModel):
    field_name: str
    data_type: str
    value: str
    source_substring: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class _GenOutput(BaseModel):
    fields: list[_ExtractedFieldOut] = Field(default_factory=list)


_VERIFY_SYSTEM = """\
You are verifying an extracted (field, value, source) triple against the
ORIGINAL document text. Decide:

- `value_supported`: True iff the document literally states this value
  (allowing minor format normalisation like "2.0%" vs "2%").
- `source_present`: True iff `source_substring` appears in the document
  (whitespace-insensitive). The substring need not be a standalone token.
- `value_in_source`: True iff the value (or its core token, e.g. "2.0%") is
  present inside `source_substring` itself.

All three must be True for us to keep the row.
"""


class _VerifyOutput(BaseModel):
    value_supported: bool
    source_present: bool
    value_in_source: bool
    reasoning: str


def _format_gen_user(doc: ParsedDoc) -> str:
    body = doc.markdown[:24_000]
    return (
        f"# Document\n"
        f"doc_id: {doc.doc_id}\n"
        f"path: {doc.source_path.name}\n\n"
        f"# Document text\n```\n{body}\n```\n"
    )


def _format_verify_user(doc: ParsedDoc, field: _ExtractedFieldOut) -> str:
    body = doc.markdown[:24_000]
    return (
        f"# Document text\n```\n{body}\n```\n\n"
        f"# Triple\n"
        f"field_name: {field.field_name}\n"
        f"data_type: {field.data_type}\n"
        f"value: {field.value}\n"
        f"source_substring: {field.source_substring}\n"
    )


def _normalize_ws(s: str) -> str:
    return " ".join(s.split()).lower()


class ExtractionSynthesizer(Synthesizer):
    kind: ClassVar[str] = "extraction"
    output_file: ClassVar[str] = "extraction_golden.jsonl"
    required_fields: ClassVar[set[str]] = set()

    async def synthesize(
        self,
        docs: list[ParsedDoc],
        *,
        n: int,
        ctx: SynthCtx,
    ) -> AsyncIterator[GoldenRow]:
        gen_system = _gen_system(ctx)
        allowed_field_names: set[str] | None = (
            {f["field_name"] for f in ctx.fields} if ctx.fields else None
        )

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
                    purpose="extraction.generate",
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("extraction.generate failed (doc=%s): %s", doc.doc_id, exc)
                continue

            normalized_doc = _normalize_ws(doc.markdown)

            for field in gen.fields:
                if emitted >= n:
                    break
                if not field.field_name or not field.value:
                    continue
                if field.confidence < 0.6:
                    continue
                if field.data_type not in _ALLOWED_DATA_TYPES:
                    logger.debug(
                        "extraction: dropping unknown data_type=%r for %s",
                        field.data_type,
                        field.field_name,
                    )
                    continue
                if allowed_field_names and field.field_name not in allowed_field_names:
                    continue

                if _normalize_ws(field.source_substring) not in normalized_doc:
                    logger.debug(
                        "local check: source_substring not in doc, skipping %s",
                        field.field_name,
                    )
                    continue

                try:
                    verdict = await judge_call(
                        ctx=ctx,
                        system=_VERIFY_SYSTEM,
                        user=_format_verify_user(doc, field),
                        schema=_VerifyOutput,
                        purpose="extraction.verify",
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("extraction.verify failed: %s", exc)
                    continue

                if not (
                    verdict.value_supported and verdict.source_present and verdict.value_in_source
                ):
                    logger.debug(
                        "extraction.verify rejected %s: %s", field.field_name, verdict.reasoning
                    )
                    continue

                row: GoldenRow = {
                    "id": f"ext_synth_{doc.doc_id}_{field.field_name}",
                    "doc_id": doc.doc_id,
                    "parsed_path": doc.parsed_path_str,
                    "field_name": field.field_name,
                    "data_type": field.data_type,
                    "expected_value": field.value,
                    "expected_source_substring": field.source_substring.strip(),
                    "tags": list({"positive", "synth", *ctx.tags}),
                    "synth": {
                        "judge_model": ctx.judge_model,
                        "source_doc_id": doc.doc_id,
                        "seed": ctx.seed,
                        "generator_confidence": field.confidence,
                        "verifier_reasoning": verdict.reasoning,
                        "domain_hint": ctx.domain_hint,
                        "schema_mode": "predefined" if ctx.fields else "discovery",
                    },
                }
                emitted += 1
                yield row

    def validate(self, row: GoldenRow) -> None:
        super().validate(row)
        for key in (
            "doc_id",
            "field_name",
            "expected_value",
            "expected_source_substring",
            "data_type",
        ):
            if not row.get(key):
                raise ValueError(f"extraction row missing/empty field: {key}")
        if row["data_type"] not in _ALLOWED_DATA_TYPES:
            raise ValueError(
                f"unknown data_type: {row['data_type']!r} (allowed: {sorted(_ALLOWED_DATA_TYPES)})"
            )
