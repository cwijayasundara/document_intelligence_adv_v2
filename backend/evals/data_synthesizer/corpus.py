"""Load parsed source documents into ParsedDoc objects."""

from __future__ import annotations

import hashlib
import logging
from glob import glob
from pathlib import Path
from typing import Iterable

from .base import Chunk, ParsedDoc

logger = logging.getLogger(__name__)

_SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt"}


def _stable_doc_id(path: Path) -> str:
    digest = hashlib.sha1(str(path.resolve()).encode("utf-8")).hexdigest()[:8]
    return f"{path.stem.replace(' ', '_')}_{digest}"


def _expand_inputs(inputs: Iterable[str | Path]) -> list[Path]:
    """Resolve globs/dirs/files into a flat, sorted, deduped list of paths."""
    seen: dict[Path, None] = {}
    for raw in inputs:
        s = str(raw)
        if any(ch in s for ch in "*?["):
            for hit in glob(s, recursive=True):
                seen.setdefault(Path(hit), None)
            continue
        p = Path(s)
        if p.is_dir():
            for sfx in _SUPPORTED_SUFFIXES:
                for hit in p.rglob(f"*{sfx}"):
                    seen.setdefault(hit, None)
        elif p.is_file():
            seen.setdefault(p, None)
        else:
            logger.warning("input not found: %s", p)
    return sorted(seen.keys())


def load_corpus(inputs: Iterable[str | Path]) -> list[ParsedDoc]:
    """Read every input path into a ParsedDoc.

    Accepts a mix of files, directories, and glob patterns. Only files with
    a supported suffix are loaded; everything else is skipped with a warning.
    """
    docs: list[ParsedDoc] = []
    for path in _expand_inputs(inputs):
        if path.suffix.lower() not in _SUPPORTED_SUFFIXES:
            logger.warning("skipping unsupported suffix: %s", path)
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            logger.warning("failed to read %s: %s", path, exc)
            continue
        docs.append(
            ParsedDoc(
                doc_id=_stable_doc_id(path),
                source_path=path,
                markdown=text,
            )
        )
    logger.info("loaded %d parsed docs from %s input(s)", len(docs), len(list(inputs)))
    return docs


def chunk_doc(doc: ParsedDoc, *, max_tokens: int = 512, overlap_tokens: int = 100) -> list[Chunk]:
    """Chunk a doc using the production chunker so synth output matches retrieval reality.

    The result is cached on `doc.chunks` so repeated calls are free.
    """
    if doc.chunks:
        return doc.chunks

    try:
        from src.rag.chunker import DocumentChunker
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "src.rag.chunker is required for chunking — run from backend/ with deps installed"
        ) from exc

    chunker = DocumentChunker(max_tokens=max_tokens, overlap_tokens=overlap_tokens)
    raw_chunks = chunker.chunk(doc.markdown)
    doc.chunks = [
        Chunk(text=c.text, index=c.index, metadata=dict(c.metadata or {}))
        for c in raw_chunks
    ]
    return doc.chunks
