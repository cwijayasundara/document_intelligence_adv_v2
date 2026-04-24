"""Push / pull golden JSONL datasets to LangSmith.

LangSmith is the authoritative system of record for eval runs. This module
syncs the local JSONL files under `backend/evals/datasets/` to LangSmith
datasets named `pe-doc-intel/<stage>` so experiments can reference them by
name.

Usage:
    from evals.dataset_sync import sync_all, sync_stage

    sync_all()                      # Push every stage
    sync_stage("extraction")        # Push one stage
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)

DATASETS_DIR = Path(__file__).parent / "datasets"

STAGE_TO_FILE = {
    "classification": "classification_golden.jsonl",
    "extraction": "extraction_golden.jsonl",
    "summary": "summary_golden.jsonl",
    "rag": "rag_golden.jsonl",
    "sql": "sql_golden.jsonl",
    "pipeline": "pipeline_golden.jsonl",
    "regression": "regression_corrections.jsonl",
    "adversarial": "adversarial_synthetic.jsonl",
}

DATASET_NAME_TEMPLATE = "pe-doc-intel/{stage}"


@dataclass
class SyncResult:
    stage: str
    dataset_name: str
    examples_total: int
    examples_created: int
    examples_updated: int
    examples_unchanged: int


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    if not path.exists():
        return
    with path.open() as f:
        for line_num, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            try:
                yield json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_num}: invalid JSON: {exc}") from exc


def _split_inputs_outputs(record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Split a golden record into LangSmith inputs (what the LLM sees) and
    outputs (ground truth it is graded against).

    Heuristic: keys prefixed `expected_` or `reference_` go to outputs, plus
    `pe_checklist`. Everything else goes to inputs. `id`, `tags`, `notes`
    become dataset-level metadata.
    """
    inputs: dict[str, Any] = {}
    outputs: dict[str, Any] = {}
    for key, value in record.items():
        if key in {"id", "tags", "notes", "source"}:
            continue
        if key.startswith("expected_") or key.startswith("reference_") or key == "pe_checklist":
            outputs[key] = value
        else:
            inputs[key] = value
    return inputs, outputs


def sync_stage(stage: str, client: Any | None = None) -> SyncResult:
    """Sync one stage's JSONL file to a LangSmith dataset.

    Args:
        stage: Key in `STAGE_TO_FILE` (e.g. "extraction").
        client: Optional `langsmith.Client`. If None, constructs a default.

    Returns:
        `SyncResult` with counts. Raises if `LANGSMITH_API_KEY` is unset.
    """
    if stage not in STAGE_TO_FILE:
        raise ValueError(f"Unknown stage '{stage}'. Known: {sorted(STAGE_TO_FILE)}")

    if client is None:
        if not os.environ.get("LANGSMITH_API_KEY"):
            raise RuntimeError("LANGSMITH_API_KEY is required to sync datasets.")
        from langsmith import Client

        client = Client()

    path = DATASETS_DIR / STAGE_TO_FILE[stage]
    dataset_name = DATASET_NAME_TEMPLATE.format(stage=stage)

    records = list(_iter_jsonl(path))
    if not records:
        logger.warning("No records in %s — skipping sync for stage %s.", path, stage)
        return SyncResult(stage, dataset_name, 0, 0, 0, 0)

    try:
        dataset = client.read_dataset(dataset_name=dataset_name)
    except Exception:
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description=f"Golden dataset for {stage} — synced from {path.name}",
        )

    existing_by_ref_id: dict[str, Any] = {}
    for example in client.list_examples(dataset_id=dataset.id):
        ref_id = (example.metadata or {}).get("ref_id")
        if ref_id:
            existing_by_ref_id[ref_id] = example

    created = 0
    updated = 0
    unchanged = 0
    for record in records:
        ref_id = record.get("id") or f"{stage}_{hash(json.dumps(record, sort_keys=True)):x}"
        inputs, outputs = _split_inputs_outputs(record)
        metadata = {
            "ref_id": ref_id,
            "tags": record.get("tags", []),
            "notes": record.get("notes", ""),
            "source_file": STAGE_TO_FILE[stage],
        }

        existing = existing_by_ref_id.get(ref_id)
        if existing is None:
            client.create_example(
                inputs=inputs,
                outputs=outputs,
                metadata=metadata,
                dataset_id=dataset.id,
            )
            created += 1
            continue

        if (
            existing.inputs == inputs
            and existing.outputs == outputs
            and (existing.metadata or {}).get("tags") == metadata["tags"]
        ):
            unchanged += 1
            continue

        client.update_example(
            example_id=existing.id,
            inputs=inputs,
            outputs=outputs,
            metadata=metadata,
        )
        updated += 1

    result = SyncResult(
        stage=stage,
        dataset_name=dataset_name,
        examples_total=len(records),
        examples_created=created,
        examples_updated=updated,
        examples_unchanged=unchanged,
    )
    logger.info(
        "Synced stage=%s dataset=%s total=%d created=%d updated=%d unchanged=%d",
        stage,
        dataset_name,
        result.examples_total,
        created,
        updated,
        unchanged,
    )
    return result


def sync_all(client: Any | None = None) -> list[SyncResult]:
    """Sync every stage whose JSONL file exists and is non-empty."""
    results: list[SyncResult] = []
    for stage in STAGE_TO_FILE:
        path = DATASETS_DIR / STAGE_TO_FILE[stage]
        if not path.exists() or path.stat().st_size == 0:
            logger.debug("Skipping empty/missing dataset for stage=%s (%s)", stage, path)
            continue
        results.append(sync_stage(stage, client=client))
    return results
