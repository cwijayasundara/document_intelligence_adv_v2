"""Run Azure document_retrieval composite over the RAG pipeline.

Provides Fidelity / NDCG / XDCG / MaxRel / Holes - none of which the existing
metric-based retrieval evaluators (Recall@K, MRR, nDCG@K) emit on their own.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from ..adapter import to_doc_retrieval_row
from ..criteria import document_retrieval
from ._base import FoundryRunResult, submit

logger = logging.getLogger(__name__)


async def run_doc_retrieval(*, subset: int | None = None) -> FoundryRunResult:
    from evals.runners._base import load_examples
    from evals.runners.run_rag import _predict

    examples = load_examples("rag_golden.jsonl", subset=subset)
    rows: list[dict[str, Any]] = []
    for ex in examples:
        try:
            outputs = await _predict(ex)
        except Exception as exc:  # noqa: BLE001
            logger.exception("rag predict failed for %s: %s", ex.id, exc)
            outputs = {"chunks": []}
        rows.append(to_doc_retrieval_row(ex.outputs or {}, outputs))

    return await submit(
        name=f"doc-retrieval-{int(time.time())}",
        rows=rows,
        testing_criteria=[document_retrieval(label_min=0, label_max=4)],
    )
