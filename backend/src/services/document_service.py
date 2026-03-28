"""Document upload service with SHA-256 dedup."""

import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Document
from src.db.repositories.documents import DocumentRepository
from src.storage.local import LocalStorage

ALLOWED_EXTENSIONS = {"pdf", "docx", "xlsx", "png", "jpg", "tiff"}


class DocumentService:
    """Handle document upload with SHA-256 dedup and file storage."""

    def __init__(self, session: AsyncSession, storage: LocalStorage) -> None:
        self._repo = DocumentRepository(session)
        self._storage = storage

    async def upload(
        self, filename: str, content: bytes
    ) -> tuple[Document, bool]:
        """Upload a document file with SHA-256 dedup.

        Returns:
            Tuple of (document, is_duplicate). If duplicate, returns existing doc.

        Raises:
            ValueError: If file type is not allowed.
        """
        file_ext = self._extract_extension(filename)
        if file_ext not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"File type '{file_ext}' not allowed. "
                f"Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        file_hash = LocalStorage.compute_sha256(content)

        existing = await self._repo.get_by_hash(file_hash)
        if existing is not None:
            return existing, True

        saved_path = await self._storage.save_file(filename, content)

        doc = await self._repo.create(
            file_name=filename,
            original_path=str(saved_path),
            file_hash=file_hash,
            file_type=file_ext,
            file_size=len(content),
        )
        return doc, False

    async def get_document(self, doc_id: uuid.UUID) -> Document | None:
        """Get a document by ID."""
        return await self._repo.get_by_id(doc_id)

    async def list_documents(
        self,
        status: str | None = None,
        category_id: uuid.UUID | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Document], int]:
        """List documents with optional filters."""
        return await self._repo.list_all(
            status=status,
            category_id=category_id,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def delete_document(self, doc_id: uuid.UUID) -> bool:
        """Delete a document and its associated files.

        Returns:
            True if document was found and deleted.
        """
        doc = await self._repo.get_by_id(doc_id)
        if doc is None:
            return False

        if doc.original_path:
            await self._storage.delete_file(doc.original_path)
        if doc.parsed_path:
            await self._storage.delete_file(doc.parsed_path)

        await self._repo.delete(doc_id)
        return True

    @staticmethod
    def _extract_extension(filename: str) -> str:
        """Extract the file extension from a filename."""
        ext = Path(filename).suffix.lstrip(".")
        return ext.lower()
