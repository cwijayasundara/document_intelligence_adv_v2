"""Repository for document category CRUD operations."""

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import DocumentCategory


class CategoryRepository:
    """Async repository for document category operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        name: str,
        description: str | None = None,
        classification_criteria: str | None = None,
    ) -> DocumentCategory:
        """Create a new document category."""
        category = DocumentCategory(
            id=uuid.uuid4(),
            name=name,
            description=description,
            classification_criteria=classification_criteria,
        )
        self._session.add(category)
        await self._session.flush()
        return category

    async def get_by_id(self, cat_id: uuid.UUID) -> DocumentCategory | None:
        """Get a category by ID."""
        stmt = select(DocumentCategory).where(DocumentCategory.id == cat_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> DocumentCategory | None:
        """Get a category by name."""
        stmt = select(DocumentCategory).where(DocumentCategory.name == name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> list[DocumentCategory]:
        """List all categories ordered by name."""
        stmt = select(DocumentCategory).order_by(DocumentCategory.name)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        cat_id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
        classification_criteria: str | None = None,
    ) -> DocumentCategory | None:
        """Update a category. Returns None if not found."""
        category = await self.get_by_id(cat_id)
        if category is None:
            return None

        if name is not None:
            category.name = name
        if description is not None:
            category.description = description
        if classification_criteria is not None:
            category.classification_criteria = classification_criteria

        await self._session.flush()
        return category

    async def delete(self, cat_id: uuid.UUID) -> bool:
        """Delete a category. Returns True if deleted."""
        stmt = delete(DocumentCategory).where(DocumentCategory.id == cat_id)
        result = await self._session.execute(stmt)
        return (result.rowcount or 0) > 0

    async def count(self) -> int:
        """Count total categories."""
        stmt = select(func.count()).select_from(DocumentCategory)
        result = await self._session.execute(stmt)
        return result.scalar() or 0
