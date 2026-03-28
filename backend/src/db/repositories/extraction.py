"""Repository for extraction schemas and fields."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import ExtractionField, ExtractionSchema


class ExtractionSchemaRepository:
    """Async repository for extraction schema operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest_for_category(self, category_id: uuid.UUID) -> ExtractionSchema | None:
        """Get the latest version schema for a category."""
        stmt = (
            select(ExtractionSchema)
            .where(ExtractionSchema.category_id == category_id)
            .order_by(ExtractionSchema.version.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        category_id: uuid.UUID,
        version: int = 1,
        schema_yaml: str | None = None,
    ) -> ExtractionSchema:
        """Create a new extraction schema version."""
        schema = ExtractionSchema(
            id=uuid.uuid4(),
            category_id=category_id,
            version=version,
            schema_yaml=schema_yaml,
        )
        self._session.add(schema)
        await self._session.flush()
        return schema

    async def get_next_version(self, category_id: uuid.UUID) -> int:
        """Get the next version number for a category's schema."""
        stmt = select(func.coalesce(func.max(ExtractionSchema.version), 0)).where(
            ExtractionSchema.category_id == category_id
        )
        result = await self._session.execute(stmt)
        current_max = result.scalar() or 0
        return current_max + 1


class ExtractionFieldRepository:
    """Async repository for extraction field operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_fields_for_schema(self, schema_id: uuid.UUID) -> list[ExtractionField]:
        """Get all fields for a schema, ordered by sort_order."""
        stmt = (
            select(ExtractionField)
            .where(ExtractionField.schema_id == schema_id)
            .order_by(ExtractionField.sort_order)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def upsert_field(
        self,
        schema_id: uuid.UUID,
        field_name: str,
        display_name: str,
        description: str | None = None,
        examples: str | None = None,
        data_type: str = "string",
        required: bool = False,
        sort_order: int = 0,
    ) -> ExtractionField:
        """Create or update a field within a schema."""
        stmt = select(ExtractionField).where(
            ExtractionField.schema_id == schema_id,
            ExtractionField.field_name == field_name,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            existing.display_name = display_name
            existing.description = description
            existing.examples = examples
            existing.data_type = data_type
            existing.required = required
            existing.sort_order = sort_order
            await self._session.flush()
            return existing

        field = ExtractionField(
            id=uuid.uuid4(),
            schema_id=schema_id,
            field_name=field_name,
            display_name=display_name,
            description=description,
            examples=examples,
            data_type=data_type,
            required=required,
            sort_order=sort_order,
        )
        self._session.add(field)
        await self._session.flush()
        return field
