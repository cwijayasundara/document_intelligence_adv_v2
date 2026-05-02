"""Pipeline (gate-routing) golden-dataset synthesizer.

`runners/run_pipeline.py` exercises two pure gate functions and the
deterministic node-visit order. There is nothing for an LLM to learn or
verify here, so this synthesizer is fully deterministic and free of judge
calls — it just emits the canonical scenarios per source document.

For every parsed doc we emit three rows (capped by `n`):
  1. happy_path           — parse passes, extraction passes
  2. extraction_review    — parse passes, extraction requires review
  3. parse_review         — parse fails (low confidence)

Output schema matches `evals/datasets/pipeline_golden.jsonl` so the existing
`runners/run_pipeline.py` consumes it unchanged.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator, ClassVar

from ..base import GoldenRow, ParsedDoc, SynthCtx, Synthesizer

logger = logging.getLogger(__name__)


_SCENARIOS: list[dict[str, object]] = [
    {
        "suffix": "happy_path",
        "stages": ["parse", "summarize", "classify", "extract", "ingest", "finalize"],
        "gates": {"parse_confidence_gate": "pass", "extraction_review_gate": "pass"},
        "expected_min_parse_confidence": 80,
        "tags": ["e2e", "happy_path"],
    },
    {
        "suffix": "extraction_review",
        "stages": [
            "parse",
            "summarize",
            "classify",
            "extract",
            "await_extraction_review",
            "ingest",
            "finalize",
        ],
        "gates": {"parse_confidence_gate": "pass", "extraction_review_gate": "requires_review"},
        "expected_min_parse_confidence": 70,
        "expected_review_reason": (
            "One or more required fields are empty or below the confidence threshold."
        ),
        "tags": ["e2e", "review_gate"],
    },
    {
        "suffix": "parse_review",
        "stages": ["parse", "await_parse_review"],
        "gates": {"parse_confidence_gate": "requires_review"},
        "expected_max_parse_confidence": 75,
        "expected_review_reason": "parse confidence below threshold",
        "tags": ["e2e", "parse_gate", "low_conf"],
    },
]


def _file_name_for(doc: ParsedDoc) -> str:
    """Best-effort PDF filename guess for the runner's `file_name` slot."""
    stem = doc.source_path.stem
    return f"{stem}.pdf"


def _row_for(doc: ParsedDoc, scenario: dict[str, object], ctx: SynthCtx) -> GoldenRow:
    row: GoldenRow = {
        "id": f"pipe_synth_{doc.doc_id}_{scenario['suffix']}",
        "doc_id": doc.doc_id,
        "file_name": _file_name_for(doc),
        "expected_stages": list(scenario["stages"]),  # type: ignore[arg-type]
        "expected_gates": dict(scenario["gates"]),  # type: ignore[arg-type]
        "tags": list({*scenario["tags"], *ctx.tags, "synth"}),  # type: ignore[misc]
        "synth": {
            "source_doc_id": doc.doc_id,
            "scenario": scenario["suffix"],
            "seed": ctx.seed,
        },
    }
    if "expected_min_parse_confidence" in scenario:
        row["expected_min_parse_confidence"] = scenario["expected_min_parse_confidence"]
    if "expected_max_parse_confidence" in scenario:
        row["expected_max_parse_confidence"] = scenario["expected_max_parse_confidence"]
    if "expected_review_reason" in scenario:
        row["expected_review_reason"] = scenario["expected_review_reason"]
    return row


class PipelineSynthesizer(Synthesizer):
    kind: ClassVar[str] = "pipeline"
    output_file: ClassVar[str] = "pipeline_golden.jsonl"
    required_fields: ClassVar[set[str]] = set()

    async def synthesize(
        self,
        docs: list[ParsedDoc],
        *,
        n: int,
        ctx: SynthCtx,
    ) -> AsyncIterator[GoldenRow]:
        emitted = 0
        # Round-robin over scenarios so every doc gets the happy_path first
        # before any doc gets parse_review — keeps small `n` runs balanced.
        for scenario in _SCENARIOS:
            for doc in docs:
                if emitted >= n:
                    return
                yield _row_for(doc, scenario, ctx)
                emitted += 1

    def validate(self, row: GoldenRow) -> None:
        super().validate(row)
        for key in ("doc_id", "file_name", "expected_stages", "expected_gates"):
            if not row.get(key):
                raise ValueError(f"pipeline row missing/empty field: {key}")
        if not isinstance(row["expected_stages"], list) or not row["expected_stages"]:
            raise ValueError("expected_stages must be a non-empty list")
        if not isinstance(row["expected_gates"], dict):
            raise ValueError("expected_gates must be a dict")
        gate_values = {"pass", "requires_review"}
        for k, v in row["expected_gates"].items():
            if v not in gate_values:
                raise ValueError(f"expected_gates[{k}]={v!r} not in {gate_values}")
        # Sanity: expected confidence is also bounded.
        for key in ("expected_min_parse_confidence", "expected_max_parse_confidence"):
            if key in row and not (0 <= float(row[key]) <= 100):
                raise ValueError(f"{key} out of range: {row[key]}")
