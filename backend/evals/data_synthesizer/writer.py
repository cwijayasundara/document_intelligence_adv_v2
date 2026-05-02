"""JSONL writer with dedup, dry-run, and reject sidecar."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

from .base import GoldenRow, Synthesizer

logger = logging.getLogger(__name__)

WriteMode = str  # one of: append | overwrite | dry-run


@dataclass
class WriteStats:
    written: int = 0
    skipped_duplicate: int = 0
    rejected_invalid: int = 0
    output_path: Path | None = None
    rejects_path: Path | None = None


def _iter_existing(path: Path) -> Iterator[GoldenRow]:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            logger.warning("malformed existing row in %s, skipping", path)


def _dedupe_key(row: GoldenRow, key_fields: list[str]) -> str:
    payload = {k: row.get(k) for k in key_fields}
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha1(blob).hexdigest()


def write_rows(
    rows: Iterable[GoldenRow],
    *,
    synthesizer: Synthesizer,
    out_path: Path,
    mode: WriteMode,
    dedupe_keys: list[str],
) -> WriteStats:
    """Write rows produced by a synthesizer to JSONL.

    - `append`: keep existing rows, dedupe by `dedupe_keys`, append new ones.
    - `overwrite`: replace the file outright (existing rows dropped).
    - `dry-run`: write to `<out>.proposed.jsonl` only, never touch the live file.
    """
    stats = WriteStats()

    if mode == "dry-run":
        target = out_path.with_suffix(out_path.suffix + ".proposed.jsonl")
        existing_keys: set[str] = set()
    elif mode == "overwrite":
        target = out_path
        existing_keys = set()
    elif mode == "append":
        target = out_path
        existing_keys = {_dedupe_key(r, dedupe_keys) for r in _iter_existing(target)}
    else:
        raise ValueError(f"unknown mode: {mode!r}")

    target.parent.mkdir(parents=True, exist_ok=True)
    rejects_path = target.with_suffix(target.suffix + ".rejects.jsonl")

    open_mode = "w" if mode == "overwrite" or mode == "dry-run" else "a"
    with target.open(open_mode, encoding="utf-8") as fh, rejects_path.open(
        "a", encoding="utf-8"
    ) as rfh:
        for row in rows:
            try:
                synthesizer.validate(row)
            except Exception as exc:  # noqa: BLE001
                stats.rejected_invalid += 1
                rfh.write(json.dumps({"reason": str(exc), "row": row}) + "\n")
                continue

            key = _dedupe_key(row, dedupe_keys)
            if key in existing_keys:
                stats.skipped_duplicate += 1
                continue
            existing_keys.add(key)
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            stats.written += 1

    stats.output_path = target
    stats.rejects_path = rejects_path if stats.rejected_invalid else None
    return stats
