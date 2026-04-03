"""Document chunker using LangChain's markdown-aware splitting.

Two-stage approach:
1. MarkdownHeaderTextSplitter — splits by document structure (Articles, Sections)
2. RecursiveCharacterTextSplitter — splits oversized chunks with overlap
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

logger = logging.getLogger(__name__)

# Markdown headers to split on — preserves LPA article/section hierarchy
_HEADERS_TO_SPLIT_ON = [
    ("#", "header_1"),
    ("##", "header_2"),
    ("###", "header_3"),
]


@dataclass
class Chunk:
    """A single text chunk with metadata."""

    text: str
    index: int
    metadata: dict[str, str] = field(default_factory=dict)


class DocumentChunker:
    """Split parsed markdown using structure-aware + size-based splitting."""

    def __init__(
        self,
        max_tokens: int = 512,
        overlap_tokens: int = 100,
        chars_per_token: int = 4,
    ) -> None:
        self._max_chars = max_tokens * chars_per_token
        self._overlap_chars = overlap_tokens * chars_per_token

        self._header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=_HEADERS_TO_SPLIT_ON,
            strip_headers=False,
        )
        self._size_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self._max_chars,
            chunk_overlap=self._overlap_chars,
            separators=["\n\n", "\n", ". ", " "],
        )

    def chunk(self, text: str) -> list[Chunk]:
        """Split markdown text into chunks preserving document structure.

        Args:
            text: The full parsed markdown content.

        Returns:
            List of Chunk objects with text, index, and header metadata.
        """
        if not text.strip():
            logger.warning("Empty document content, no chunks to generate")
            return []

        logger.info(
            "Stage 1: splitting %d chars by markdown headers (#, ##, ###)",
            len(text),
        )
        header_docs: list[Document] = self._header_splitter.split_text(text)
        logger.info(
            "Stage 1 complete: %d header-based sections (max_chunk=%d chars, overlap=%d chars)",
            len(header_docs),
            self._max_chars,
            self._overlap_chars,
        )

        logger.info("Stage 2: splitting oversized sections with RecursiveCharacterTextSplitter")
        final_docs: list[Document] = self._size_splitter.split_documents(
            header_docs
        )

        chunks = []
        for idx, doc in enumerate(final_docs):
            chunks.append(
                Chunk(
                    text=doc.page_content,
                    index=idx,
                    metadata=dict(doc.metadata),
                )
            )

        avg_chars = sum(len(c.text) for c in chunks) // max(len(chunks), 1)
        logger.info(
            "Chunking complete: %d sections -> %d chunks (avg %d chars/chunk)",
            len(header_docs),
            len(chunks),
            avg_chars,
        )
        return chunks
