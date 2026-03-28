"""Configuration API endpoints for categories and extraction fields."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_session
from src.api.schemas.config import (
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdate,
    FieldResponse,
    FieldsCreateRequest,
    FieldsCreateResponse,
    FieldsListResponse,
)
from src.db.repositories.categories import CategoryRepository
from src.db.repositories.documents import DocumentRepository
from src.db.repositories.extraction import (
    ExtractionFieldRepository,
    ExtractionSchemaRepository,
)

router = APIRouter()


@router.get(
    "/config/categories",
    response_model=CategoryListResponse,
    summary="List all categories",
)
async def list_categories(
    session: AsyncSession = Depends(get_session),
) -> CategoryListResponse:
    """Return all document categories."""
    repo = CategoryRepository(session)
    categories = await repo.list_all()
    items = [CategoryResponse.model_validate(c) for c in categories]
    return CategoryListResponse(categories=items)


@router.post(
    "/config/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category",
)
async def create_category(
    body: CategoryCreate,
    session: AsyncSession = Depends(get_session),
) -> CategoryResponse:
    """Create a new document category."""
    repo = CategoryRepository(session)
    category = await repo.create(
        name=body.name,
        description=body.description,
        classification_criteria=body.classification_criteria,
    )
    return CategoryResponse.model_validate(category)


@router.put(
    "/config/categories/{cat_id}",
    response_model=CategoryResponse,
    summary="Update a category",
)
async def update_category(
    cat_id: uuid.UUID,
    body: CategoryUpdate,
    session: AsyncSession = Depends(get_session),
) -> CategoryResponse:
    """Update an existing category."""
    repo = CategoryRepository(session)
    category = await repo.update(
        cat_id=cat_id,
        name=body.name,
        description=body.description,
        classification_criteria=body.classification_criteria,
    )
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return CategoryResponse.model_validate(category)


@router.delete(
    "/config/categories/{cat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a category",
)
async def delete_category(
    cat_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a category. Fails if documents are assigned."""
    cat_repo = CategoryRepository(session)
    doc_repo = DocumentRepository(session)

    category = await cat_repo.get_by_id(cat_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    doc_count = await doc_repo.count_by_category(cat_id)
    if doc_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category with assigned documents",
        )

    await cat_repo.delete(cat_id)


@router.get(
    "/config/categories/{cat_id}/fields",
    response_model=FieldsListResponse,
    summary="List extraction fields for a category",
)
async def list_fields(
    cat_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> FieldsListResponse:
    """Return extraction fields for a category, ordered by sort_order."""
    cat_repo = CategoryRepository(session)
    category = await cat_repo.get_by_id(cat_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    schema_repo = ExtractionSchemaRepository(session)
    schema = await schema_repo.get_latest_for_category(cat_id)

    if schema is None:
        return FieldsListResponse(
            category_id=cat_id,
            category_name=category.name,
            schema_version=0,
            fields=[],
        )

    field_repo = ExtractionFieldRepository(session)
    fields = await field_repo.get_fields_for_schema(schema.id)
    field_items = [FieldResponse.model_validate(f) for f in fields]

    return FieldsListResponse(
        category_id=cat_id,
        category_name=category.name,
        schema_version=schema.version,
        fields=field_items,
    )


@router.post(
    "/config/categories/{cat_id}/fields",
    response_model=FieldsCreateResponse,
    summary="Create/update extraction fields",
)
async def create_fields(
    cat_id: uuid.UUID,
    body: FieldsCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> FieldsCreateResponse:
    """Create or update extraction fields for a category."""
    cat_repo = CategoryRepository(session)
    category = await cat_repo.get_by_id(cat_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    schema_repo = ExtractionSchemaRepository(session)
    next_version = await schema_repo.get_next_version(cat_id)
    schema = await schema_repo.create(
        category_id=cat_id,
        version=next_version,
    )

    field_repo = ExtractionFieldRepository(session)
    created = 0
    updated = 0

    for field_def in body.fields:
        # Check if field existed in previous schema version
        existing_schema = await schema_repo.get_latest_for_category(cat_id)
        is_new = True
        if existing_schema and existing_schema.id != schema.id:
            from sqlalchemy import select as sa_select

            from src.db.models import ExtractionField

            stmt = sa_select(ExtractionField).where(
                ExtractionField.schema_id == existing_schema.id,
                ExtractionField.field_name == field_def.field_name,
            )
            result = await session.execute(stmt)
            if result.scalar_one_or_none() is not None:
                is_new = False

        await field_repo.upsert_field(
            schema_id=schema.id,
            field_name=field_def.field_name,
            display_name=field_def.display_name,
            description=field_def.description,
            examples=field_def.examples,
            data_type=field_def.data_type,
            required=field_def.required,
            sort_order=field_def.sort_order,
        )

        if is_new:
            created += 1
        else:
            updated += 1

    return FieldsCreateResponse(
        category_id=cat_id,
        schema_version=next_version,
        fields_created=created,
        fields_updated=updated,
    )
