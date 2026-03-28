"""Repository for extraction results (extracted_values table)."""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import ExtractedValue, ExtractionField


class ExtractedValuesRepository:
    """Async repository for extracted value CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_results(
        self,
        document_id: uuid.UUID,
        results: list[dict],
    ) -> list[ExtractedValue]:
        """Save extraction results for a document.

        Args:
            document_id: UUID of the document.
            results: List of dicts with field_id, extracted_value,
                source_text, confidence, confidence_reasoning,
                requires_review.

        Returns:
            List of created ExtractedValue records.
        """
        created = []
        for r in results:
            ev = ExtractedValue(
                id=uuid.uuid4(),
                document_id=document_id,
                field_id=r["field_id"],
                extracted_value=r.get("extracted_value", ""),
                source_text=r.get("source_text", ""),
                confidence=r.get("confidence", "medium"),
                confidence_reasoning=r.get("confidence_reasoning", ""),
                requires_review=r.get("requires_review", False),
                reviewed=False,
            )
            self._session.add(ev)
            created.append(ev)
        await self._session.flush()
        return created

    async def get_by_document_id(self, document_id: uuid.UUID) -> list[ExtractedValue]:
        """Get all extracted values for a document."""
        stmt = (
            select(ExtractedValue)
            .where(ExtractedValue.document_id == document_id)
            .order_by(ExtractedValue.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_values(self, updates: list[dict]) -> int:
        """Update extracted values and mark as reviewed.

        Args:
            updates: List of dicts with id, extracted_value, reviewed.

        Returns:
            Number of records updated.
        """
        count = 0
        for u in updates:
            stmt = (
                update(ExtractedValue)
                .where(ExtractedValue.id == u["field_id"])
                .values(
                    extracted_value=u.get("extracted_value"),
                    reviewed=u.get("reviewed", True),
                )
            )
            result = await self._session.execute(stmt)
            count += result.rowcount or 0
        await self._session.flush()
        return count

    async def get_unreviewed_fields(self, document_id: uuid.UUID) -> list[str]:
        """Get field names that require review but haven't been reviewed."""
        stmt = (
            select(ExtractionField.field_name)
            .join(
                ExtractedValue,
                ExtractedValue.field_id == ExtractionField.id,
            )
            .where(
                ExtractedValue.document_id == document_id,
                ExtractedValue.requires_review.is_(True),
                ExtractedValue.reviewed.is_(False),
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
