"""RAG golden-dataset synthesizer.

Workflow per chunk:
1. Generator judge writes a question that is fully answerable from the chunk
   plus the reference answer and 1–3 verbatim substrings the answer hinges on.
2. Verifier judge re-reads ONLY the chunk and the candidate Q/A and decides
   if the answer is entailed. If not, the row is dropped.
3. Output rows match `evals/datasets/rag_golden.jsonl` schema so they're
   drop-in for `runners/run_rag.py`.
"""

from __future__ import annotations

import logging
import random
from typing import AsyncIterator, ClassVar

from pydantic import BaseModel, Field

from ..base import Chunk, GoldenRow, ParsedDoc, SynthCtx, Synthesizer
from ..corpus import chunk_doc
from ..judge import judge_call

logger = logging.getLogger(__name__)


_GEN_SYSTEM_BASE = """\
You are an expert analyst building a retrieval-augmented-generation evaluation
dataset for a document Q&A system{domain_clause}.

Given a single document chunk, write ONE realistic question that:
- A subject-matter reader would actually ask of this kind of document.
- Is fully and unambiguously answerable from THIS chunk alone (no outside knowledge).
- Avoids yes/no phrasing where possible — prefer "what", "how much", "who", "when".
- Is concise (under 25 words).

Then provide:
- `reference_answer`: a precise 1–2 sentence answer.
- `expected_answer_contains`: 1–3 verbatim substrings (numbers, names, percentages,
  identifiers) that any correct answer MUST include. Pick the load-bearing tokens.
- `expected_relevant_chunk_substrings`: 1–3 verbatim substrings copied from the
  source chunk that prove the answer. These must appear character-for-character.
- `tags`: from {{single_hop, numeric, entity, temporal, definitional}}, pick the 1–2
  that fit best.

If the chunk is boilerplate (table-of-contents, signatures, page numbers, headers)
and no useful question exists, set `skip=true` and leave the other fields empty.
"""


def _gen_system(domain_hint: str | None) -> str:
    clause = f" over {domain_hint}" if domain_hint else ""
    return _GEN_SYSTEM_BASE.format(domain_clause=clause)


class _GenOutput(BaseModel):
    skip: bool = Field(default=False)
    question: str = Field(default="")
    reference_answer: str = Field(default="")
    expected_answer_contains: list[str] = Field(default_factory=list)
    expected_relevant_chunk_substrings: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


_VERIFY_SYSTEM = """\
You are a strict evaluator. You will be shown a document chunk and a candidate
question / reference answer. Decide:

1. `entailed`: True iff every claim in the reference answer is supported
   by the chunk (no outside knowledge, no unsupported numbers/names).
2. `answer_grounded`: True iff each item in `expected_answer_contains`
   actually appears in the chunk verbatim (case-insensitive).
3. `chunk_substrings_present`: True iff each `expected_relevant_chunk_substrings`
   item is present verbatim in the chunk.

Return all three as booleans plus a one-sentence `reasoning`.
"""


class _VerifyOutput(BaseModel):
    entailed: bool
    answer_grounded: bool
    chunk_substrings_present: bool
    reasoning: str


def _format_user_prompt_gen(doc: ParsedDoc, chunk: Chunk) -> str:
    return (
        f"# Document\n"
        f"doc_id: {doc.doc_id}\n"
        f"path: {doc.source_path.name}\n\n"
        f"# Chunk (index={chunk.index})\n"
        f"```\n{chunk.text}\n```\n"
    )


def _format_user_prompt_verify(chunk: Chunk, gen: _GenOutput) -> str:
    return (
        f"# Chunk\n```\n{chunk.text}\n```\n\n"
        f"# Candidate\n"
        f"question: {gen.question}\n"
        f"reference_answer: {gen.reference_answer}\n"
        f"expected_answer_contains: {gen.expected_answer_contains}\n"
        f"expected_relevant_chunk_substrings: {gen.expected_relevant_chunk_substrings}\n"
    )


def _select_chunks(docs: list[ParsedDoc], n: int, rng: random.Random) -> list[tuple[ParsedDoc, Chunk]]:
    """Round-robin diverse sampling: take chunks from each doc in turn until we have n."""
    pool: list[tuple[ParsedDoc, Chunk]] = []
    chunk_lists = [chunk_doc(d) for d in docs]
    max_len = max((len(c) for c in chunk_lists), default=0)
    for i in range(max_len):
        for doc, chunks in zip(docs, chunk_lists):
            if i < len(chunks):
                # Skip clearly empty / tiny chunks (boilerplate).
                if len(chunks[i].text.strip()) >= 120:
                    pool.append((doc, chunks[i]))
    rng.shuffle(pool)
    return pool[: n * 3]  # 3x oversample so verification rejects don't starve us.


class RAGSynthesizer(Synthesizer):
    kind: ClassVar[str] = "rag"
    output_file: ClassVar[str] = "rag_golden.jsonl"
    required_fields: ClassVar[set[str]] = {"chunks"}

    async def synthesize(
        self,
        docs: list[ParsedDoc],
        *,
        n: int,
        ctx: SynthCtx,
    ) -> AsyncIterator[GoldenRow]:
        rng = random.Random(ctx.seed)
        candidates = _select_chunks(docs, n, rng)
        gen_system = _gen_system(ctx.domain_hint)
        emitted = 0
        for idx, (doc, chunk) in enumerate(candidates):
            if emitted >= n:
                break
            try:
                gen = await judge_call(
                    ctx=ctx,
                    system=gen_system,
                    user=_format_user_prompt_gen(doc, chunk),
                    schema=_GenOutput,
                    purpose="rag.generate",
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("rag.generate failed (doc=%s chunk=%d): %s", doc.doc_id, chunk.index, exc)
                continue

            if gen.skip or not gen.question or not gen.reference_answer:
                continue

            try:
                verdict = await judge_call(
                    ctx=ctx,
                    system=_VERIFY_SYSTEM,
                    user=_format_user_prompt_verify(chunk, gen),
                    schema=_VerifyOutput,
                    purpose="rag.verify",
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("rag.verify failed: %s", exc)
                continue

            if not (verdict.entailed and verdict.chunk_substrings_present):
                logger.debug("rag.verify rejected: %s", verdict.reasoning)
                continue

            row: GoldenRow = {
                "id": f"rag_synth_{doc.doc_id}_{chunk.index}_{idx}",
                "doc_id": doc.doc_id,
                "query": gen.question.strip(),
                "reference_answer": gen.reference_answer.strip(),
                "expected_answer_contains": gen.expected_answer_contains,
                "expected_relevant_chunk_substrings": gen.expected_relevant_chunk_substrings,
                "expected_min_citations": 1,
                "tags": list({*gen.tags, *ctx.tags, "synth"}),
                "synth": {
                    "judge_model": ctx.judge_model,
                    "source_doc_id": doc.doc_id,
                    "source_chunk_index": chunk.index,
                    "seed": ctx.seed,
                    "verifier_reasoning": verdict.reasoning,
                },
            }
            emitted += 1
            yield row

    def validate(self, row: GoldenRow) -> None:
        super().validate(row)
        for key in ("doc_id", "query", "reference_answer", "expected_answer_contains"):
            if not row.get(key):
                raise ValueError(f"rag row missing/empty field: {key}")
        if not isinstance(row["expected_answer_contains"], list):
            raise ValueError("expected_answer_contains must be a list")
