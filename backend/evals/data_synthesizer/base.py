"""Base types for synthesizers — Synthesizer ABC, ParsedDoc, SynthCtx, GoldenRow."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, ClassVar

logger = logging.getLogger(__name__)

GoldenRow = dict[str, Any]


@dataclass
class Chunk:
    text: str
    index: int
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class ParsedDoc:
    """A parsed source document.

    Synthesizers consume these. `chunks` is populated lazily by `corpus.chunk()`
    when a synthesizer requires it.
    """

    doc_id: str
    source_path: Path
    markdown: str
    chunks: list[Chunk] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def parsed_path_str(self) -> str:
        """Path string used by runners that load fixtures from `data/parsed/...`."""
        return str(self.source_path)


@dataclass
class CostMeter:
    """Tracks judge usage so a run can abort cleanly past `max_cost_usd`."""

    max_cost_usd: float | None = None
    calls: int = 0
    estimated_usd: float = 0.0

    def record(self, usd: float) -> None:
        self.calls += 1
        self.estimated_usd += usd

    def exceeded(self) -> bool:
        return self.max_cost_usd is not None and self.estimated_usd >= self.max_cost_usd


@dataclass
class SynthCtx:
    """Per-run context shared across synthesizers."""

    seed: int = 0
    tags: list[str] = field(default_factory=list)
    concurrency: int = 4
    judge_model: str | None = None
    cost_meter: CostMeter = field(default_factory=CostMeter)
    semaphore: asyncio.Semaphore | None = None
    # Optional one-line description of the corpus, e.g. "private equity LPAs"
    # or "medical case reports". Injected into generator prompts so the judge
    # can tune phrasing/persona without the synthesizer hardcoding a vertical.
    domain_hint: str | None = None
    # Required for the classification kind, ignored elsewhere. Each entry is
    # a label name; an entry may also be a "name: criteria" string with the
    # description after a colon.
    categories: list[str] = field(default_factory=list)
    # Optional pre-defined extraction fields for the extraction kind. Each
    # entry is {"field_name": str, "data_type": str}. When empty, the
    # extraction synthesizer runs in discovery mode and lets the judge
    # propose extractable fields from the document text.
    fields: list[dict[str, str]] = field(default_factory=list)

    def get_semaphore(self) -> asyncio.Semaphore:
        if self.semaphore is None:
            self.semaphore = asyncio.Semaphore(max(1, self.concurrency))
        return self.semaphore


class Synthesizer(ABC):
    """Base class for golden-dataset synthesizers.

    Subclasses declare their `kind`, default output filename, and which
    `ParsedDoc` fields they need (`required_fields`). The CLI loads the
    corpus, invokes `synthesize()`, and writes rows via `writer.py`.
    """

    kind: ClassVar[str]
    output_file: ClassVar[str]
    required_fields: ClassVar[set[str]] = set()

    @abstractmethod
    async def synthesize(
        self,
        docs: list[ParsedDoc],
        *,
        n: int,
        ctx: SynthCtx,
    ) -> AsyncIterator[GoldenRow]:
        """Yield golden rows. Skipped/rejected rows must NOT be yielded —
        return them via the writer's reject channel by raising or by yielding
        a tagged dict; for now, just skip silently and log."""

    def validate(self, row: GoldenRow) -> None:
        """Optional — raise ValueError on a malformed row.

        Default: require an `id` field. Subclasses extend with stage-specific keys.
        """
        if "id" not in row or not row["id"]:
            raise ValueError(f"row missing 'id': {row!r}")
