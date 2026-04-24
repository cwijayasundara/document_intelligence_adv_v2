"""Harvest user corrections from long-term memory into a regression dataset.

Every time a user corrects a classification or extraction, the correction is
written to LangGraph's long-term memory under one of:

    namespaces = ["classification_corrections", "extraction_corrections"]

This script walks those namespaces and materialises them as a JSONL dataset
we then replay as regression tests. New corrections become new regressions
automatically — closing the dogfood loop.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

OUTPUT_PATH = Path(__file__).parent / "datasets" / "regression_corrections.jsonl"


async def _harvest_namespace(namespace: str) -> list[dict[str, Any]]:
    """Load all corrections under a namespace across every user."""
    from src.graph_nodes.memory.store import load_all_corrections

    try:
        return await load_all_corrections(namespace, limit=10_000)
    except Exception as exc:  # noqa: BLE001 — store errors degrade to empty harvest.
        logger.warning("Failed to load namespace=%s: %s", namespace, exc)
        return []


def _to_regression_record(namespace: str, record: dict[str, Any]) -> dict[str, Any]:
    """Shape a raw correction into a regression golden record."""
    stage = "classification" if "classification" in namespace else "extraction"
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    key = record.get("key", "unknown")
    ts = record.get("created_at") or record.get("updated_at") or record.get("ts", "0")
    return {
        "id": f"reg_{stage}_{key}_{ts}",
        "source_stage": stage,
        "harvested_at": datetime.now(timezone.utc).isoformat(),
        "tags": ["regression", "correction", stage],
        "input": record.get("input") or data.get("input"),
        "predicted_value": record.get("predicted") or data.get("predicted"),
        "expected_value": record.get("corrected") or data.get("corrected"),
        "reason": record.get("reason") or data.get("reason"),
        "raw": record,
    }


async def harvest() -> int:
    """Write the regression JSONL and return the number of records written."""
    from src.graph_nodes.memory.store import is_ephemeral_store

    namespaces = ["classification_corrections", "extraction_corrections"]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    for ns in namespaces:
        raw = await _harvest_namespace(ns)
        for r in raw:
            records.append(_to_regression_record(ns, r))

    with OUTPUT_PATH.open("w") as f:
        for r in records:
            f.write(json.dumps(r, default=str) + "\n")

    logger.info("Harvested %d corrections → %s", len(records), OUTPUT_PATH)

    if not records and is_ephemeral_store():
        logger.warning(
            "Long-term memory is backed by an in-process store, so corrections "
            "written by other processes (e.g. the API server) are not visible "
            "here. Install a persistent LangGraph Store backend and wire it "
            "into get_memory_store() to make harvest cross-process."
        )

    return len(records)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    count = asyncio.run(harvest())
    print(f"Wrote {count} regression records to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
