"""Tests for CategoryRepository and ExtractionField repositories."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.categories import CategoryRepository
from src.db.repositories.extraction import (
    ExtractionFieldRepository,
    ExtractionSchemaRepository,
)
from tests.db_helpers import create_test_session


@pytest.fixture
async def session():
    factory = await create_test_session()
    async with factory() as session:
        yield session


# --- CategoryRepository tests ---


async def test_create_category(session: AsyncSession) -> None:
    """Creating a category returns expected fields."""
    repo = CategoryRepository(session)
    cat = await repo.create(
        name="LPA",
        description="Limited Partnership Agreements",
        classification_criteria="LPA docs...",
    )
    assert cat.name == "LPA"
    assert cat.description == "Limited Partnership Agreements"
    assert isinstance(cat.id, uuid.UUID)


async def test_get_by_id(session: AsyncSession) -> None:
    """get_by_id returns category or None."""
    repo = CategoryRepository(session)
    cat = await repo.create(name="Sub Agreement")
    found = await repo.get_by_id(cat.id)
    assert found is not None
    assert found.name == "Sub Agreement"

    missing = await repo.get_by_id(uuid.uuid4())
    assert missing is None


async def test_get_by_name(session: AsyncSession) -> None:
    """get_by_name returns category by name."""
    repo = CategoryRepository(session)
    await repo.create(name="PPM")
    found = await repo.get_by_name("PPM")
    assert found is not None
    assert found.name == "PPM"


async def test_list_all(session: AsyncSession) -> None:
    """list_all returns all categories ordered by name."""
    repo = CategoryRepository(session)
    await repo.create(name="B-Cat")
    await repo.create(name="A-Cat")
    cats = await repo.list_all()
    assert len(cats) == 2
    assert cats[0].name == "A-Cat"
    assert cats[1].name == "B-Cat"


async def test_update_category(session: AsyncSession) -> None:
    """update modifies category fields."""
    repo = CategoryRepository(session)
    cat = await repo.create(name="Old Name")
    updated = await repo.update(cat.id, name="New Name", description="Updated")
    assert updated is not None
    assert updated.name == "New Name"
    assert updated.description == "Updated"


async def test_update_nonexistent(session: AsyncSession) -> None:
    """update returns None for nonexistent category."""
    repo = CategoryRepository(session)
    result = await repo.update(uuid.uuid4(), name="X")
    assert result is None


async def test_delete_category(session: AsyncSession) -> None:
    """delete removes a category."""
    repo = CategoryRepository(session)
    cat = await repo.create(name="DeleteMe")
    result = await repo.delete(cat.id)
    assert result is True
    assert await repo.get_by_id(cat.id) is None


async def test_count(session: AsyncSession) -> None:
    """count returns the number of categories."""
    repo = CategoryRepository(session)
    assert await repo.count() == 0
    await repo.create(name="Cat1")
    assert await repo.count() == 1


# --- ExtractionSchemaRepository tests ---


async def test_create_schema(session: AsyncSession) -> None:
    """Creating an extraction schema."""
    cat_repo = CategoryRepository(session)
    cat = await cat_repo.create(name="TestCat")

    schema_repo = ExtractionSchemaRepository(session)
    schema = await schema_repo.create(category_id=cat.id, version=1)
    assert schema.category_id == cat.id
    assert schema.version == 1


async def test_get_latest_for_category(session: AsyncSession) -> None:
    """get_latest_for_category returns the highest version."""
    cat_repo = CategoryRepository(session)
    cat = await cat_repo.create(name="VersionCat")

    schema_repo = ExtractionSchemaRepository(session)
    await schema_repo.create(category_id=cat.id, version=1)
    await schema_repo.create(category_id=cat.id, version=2)

    latest = await schema_repo.get_latest_for_category(cat.id)
    assert latest is not None
    assert latest.version == 2


async def test_get_next_version(session: AsyncSession) -> None:
    """get_next_version returns current max + 1."""
    cat_repo = CategoryRepository(session)
    cat = await cat_repo.create(name="VersionNext")

    schema_repo = ExtractionSchemaRepository(session)
    assert await schema_repo.get_next_version(cat.id) == 1
    await schema_repo.create(category_id=cat.id, version=1)
    assert await schema_repo.get_next_version(cat.id) == 2


# --- ExtractionFieldRepository tests ---


async def test_upsert_field_creates(session: AsyncSession) -> None:
    """upsert_field creates a new field."""
    cat_repo = CategoryRepository(session)
    cat = await cat_repo.create(name="FieldCat")

    schema_repo = ExtractionSchemaRepository(session)
    schema = await schema_repo.create(category_id=cat.id)

    field_repo = ExtractionFieldRepository(session)
    field = await field_repo.upsert_field(
        schema_id=schema.id,
        field_name="fund_name",
        display_name="Fund Name",
        description="Official fund name",
        data_type="string",
        required=True,
        sort_order=1,
    )
    assert field.field_name == "fund_name"
    assert field.required is True


async def test_upsert_field_updates_existing(session: AsyncSession) -> None:
    """upsert_field updates an existing field."""
    cat_repo = CategoryRepository(session)
    cat = await cat_repo.create(name="UpsertCat")

    schema_repo = ExtractionSchemaRepository(session)
    schema = await schema_repo.create(category_id=cat.id)

    field_repo = ExtractionFieldRepository(session)
    await field_repo.upsert_field(
        schema_id=schema.id,
        field_name="fee_rate",
        display_name="Fee Rate",
    )
    updated = await field_repo.upsert_field(
        schema_id=schema.id,
        field_name="fee_rate",
        display_name="Management Fee Rate",
        required=True,
    )
    assert updated.display_name == "Management Fee Rate"
    assert updated.required is True


async def test_get_fields_for_schema(session: AsyncSession) -> None:
    """get_fields_for_schema returns fields ordered by sort_order."""
    cat_repo = CategoryRepository(session)
    cat = await cat_repo.create(name="FieldListCat")

    schema_repo = ExtractionSchemaRepository(session)
    schema = await schema_repo.create(category_id=cat.id)

    field_repo = ExtractionFieldRepository(session)
    await field_repo.upsert_field(
        schema_id=schema.id,
        field_name="b_field",
        display_name="B Field",
        sort_order=2,
    )
    await field_repo.upsert_field(
        schema_id=schema.id,
        field_name="a_field",
        display_name="A Field",
        sort_order=1,
    )

    fields = await field_repo.get_fields_for_schema(schema.id)
    assert len(fields) == 2
    assert fields[0].field_name == "a_field"
    assert fields[1].field_name == "b_field"
