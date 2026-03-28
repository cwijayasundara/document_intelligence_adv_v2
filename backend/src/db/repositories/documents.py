"""Document repository with async CRUD operations."""

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Document


class DocumentRepository:
    """Async repository for document CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        file_name: str,
        original_path: str,
        file_hash: str,
        file_type: str,
        file_size: int,
        status: str = "uploaded",
    ) -> Document:
        """Create a new document record."""
        doc = Document(
            id=uuid.uuid4(),
            file_name=file_name,
            original_path=original_path,
            file_hash=file_hash,
            file_type=file_type,
            file_size=file_size,
            status=status,
        )
        self._session.add(doc)
        await self._session.flush()
        return doc

    async def get_by_id(self, doc_id: uuid.UUID) -> Document | None:
        """Get a document by ID."""
        stmt = select(Document).where(Document.id == doc_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_hash(self, file_hash: str) -> Document | None:
        """Get a document by file hash (for dedup)."""
        stmt = select(Document).where(Document.file_hash == file_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        status: str | None = None,
        category_id: uuid.UUID | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Document], int]:
        """List documents with optional filters and sorting."""
        stmt = select(Document)
        count_stmt = select(func.count()).select_from(Document)

        if status is not None:
            stmt = stmt.where(Document.status == status)
            count_stmt = count_stmt.where(Document.status == status)
        if category_id is not None:
            stmt = stmt.where(Document.document_category_id == category_id)
            count_stmt = count_stmt.where(
                Document.document_category_id == category_id
            )

        sort_column = getattr(Document, sort_by, Document.created_at)
        if sort_order == "asc":
            stmt = stmt.order_by(sort_column.asc())
        else:
            stmt = stmt.order_by(sort_column.desc())

        result = await self._session.execute(stmt)
        docs = list(result.scalars().all())

        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar() or 0

        return docs, total

    async def delete(self, doc_id: uuid.UUID) -> bool:
        """Delete a document by ID. Returns True if deleted."""
        stmt = delete(Document).where(Document.id == doc_id)
        result = await self._session.execute(stmt)
        return (result.rowcount or 0) > 0

    async def count_by_category(self, category_id: uuid.UUID) -> int:
        """Count documents assigned to a category."""
        stmt = (
            select(func.count())
            .select_from(Document)
            .where(Document.document_category_id == category_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0
