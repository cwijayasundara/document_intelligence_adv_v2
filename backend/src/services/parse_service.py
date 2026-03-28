"""Parse service for document parsing, content retrieval, and editing."""

from __future__ import annotations

import uuid
from pathlib import Path

import aiofiles

from src.db.models import Document
from src.db.repositories.documents import DocumentRepository
from src.parser.reducto import ReductoClient
from src.services.state_machine import validate_transition
from src.storage.local import LocalStorage


class ParseService:
    """Orchestrate document parsing via Reducto and content management."""

    def __init__(
        self,
        repo: DocumentRepository,
        storage: LocalStorage,
        reducto_client: ReductoClient,
    ) -> None:
        self._repo = repo
        self._storage = storage
        self._reducto = reducto_client

    async def parse_document(self, doc_id: uuid.UUID) -> tuple[Document, str, bool]:
        """Parse a document via Reducto.

        Returns:
            Tuple of (document, markdown_content, was_skipped).
            was_skipped is True if the parsed file already existed.

        Raises:
            ValueError: If document not found or invalid state.
        """
        doc = await self._repo.get_by_id(doc_id)
        if doc is None:
            raise ValueError(f"Document {doc_id} not found")

        parsed_path = self._storage.parsed_dir / f"{doc_id}.md"

        if parsed_path.exists() and doc.parsed_path:
            content = await self._read_file(parsed_path)
            return doc, content, True

        validate_transition(doc.status, "parsed")

        content = await self._reducto.parse(doc.original_path)

        await self._write_file(parsed_path, content)

        doc.parsed_path = str(parsed_path)
        doc.status = "parsed"
        await self._repo._session.flush()

        return doc, content, False

    async def get_parsed_content(self, doc_id: uuid.UUID) -> str | None:
        """Get parsed markdown content for a document.

        Returns:
            Markdown content string, or None if not parsed.
        """
        doc = await self._repo.get_by_id(doc_id)
        if doc is None:
            return None

        if not doc.parsed_path:
            return None

        path = Path(doc.parsed_path)
        if not path.exists():
            return None

        return await self._read_file(path)

    async def save_edited_content(self, doc_id: uuid.UUID, content: str) -> Document:
        """Save edited markdown content and transition to edited status.

        Raises:
            ValueError: If document not found or invalid state.
        """
        doc = await self._repo.get_by_id(doc_id)
        if doc is None:
            raise ValueError(f"Document {doc_id} not found")

        validate_transition(doc.status, "edited")

        parsed_path = self._storage.parsed_dir / f"{doc_id}.md"
        await self._write_file(parsed_path, content)

        doc.parsed_path = str(parsed_path)
        doc.status = "edited"
        await self._repo._session.flush()

        return doc

    @staticmethod
    async def _read_file(path: Path) -> str:
        """Read text content from a file."""
        async with aiofiles.open(path, "r") as f:
            return await f.read()

    @staticmethod
    async def _write_file(path: Path, content: str) -> None:
        """Write text content to a file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, "w") as f:
            await f.write(content)
