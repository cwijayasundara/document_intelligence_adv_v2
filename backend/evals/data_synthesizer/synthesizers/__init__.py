"""Synthesizer registry.

Each synthesizer registers under a `kind` string. The CLI maps `--kind <name>`
straight onto these classes.
"""

from __future__ import annotations

from typing import Type

from ..base import Synthesizer
from .classification import ClassificationSynthesizer
from .extraction import ExtractionSynthesizer
from .pipeline import PipelineSynthesizer
from .rag import RAGSynthesizer
from .sql import SqlSynthesizer
from .summary import SummarySynthesizer

_REGISTRY: dict[str, Type[Synthesizer]] = {
    RAGSynthesizer.kind: RAGSynthesizer,
    ExtractionSynthesizer.kind: ExtractionSynthesizer,
    ClassificationSynthesizer.kind: ClassificationSynthesizer,
    SummarySynthesizer.kind: SummarySynthesizer,
    SqlSynthesizer.kind: SqlSynthesizer,
    PipelineSynthesizer.kind: PipelineSynthesizer,
}


def list_kinds() -> list[str]:
    return sorted(_REGISTRY)


def get_synthesizer(kind: str) -> Synthesizer:
    try:
        cls = _REGISTRY[kind]
    except KeyError as exc:
        raise KeyError(f"unknown synthesizer kind: {kind!r} (available: {list_kinds()})") from exc
    return cls()


__all__ = ["get_synthesizer", "list_kinds"]
