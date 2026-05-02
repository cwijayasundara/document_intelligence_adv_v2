"""Golden dataset synthesizer.

Build per-stage golden JSONL files from parsed source documents using a
two-model generate-then-verify loop. Output is drop-in compatible with the
existing runners under `evals/runners/`.

Public surface:
    from evals.data_synthesizer import get_synthesizer, list_kinds
    from evals.data_synthesizer.corpus import load_corpus
    from evals.data_synthesizer.base import SynthCtx
"""

from __future__ import annotations

from .base import GoldenRow, ParsedDoc, SynthCtx, Synthesizer
from .synthesizers import get_synthesizer, list_kinds

__all__ = [
    "GoldenRow",
    "ParsedDoc",
    "SynthCtx",
    "Synthesizer",
    "get_synthesizer",
    "list_kinds",
]
