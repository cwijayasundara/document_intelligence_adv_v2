"""Tests for DocumentRepository using SQLite async in-memory DB."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.documents import DocumentRepository
from tests.db_helpers import create_test_session


@pytest.fixture
async def session():
    factory = await create_test_session()
    async with factory() as session:
        yield session


@pytest.fixture
def repo(session: AsyncSession) -> DocumentRepository:
    return DocumentRepository(session)


async def test_create_document(repo: DocumentRepository) -> None:
    """Creating a document returns a Document with correct fields."""
    doc = await repo.create(
        file_name="test.pdf",
        original_path="/data/upload/test.pdf",
        file_hash="abc123",
        file_type="pdf",
        file_size=1024,
    )
    assert doc.file_name == "test.pdf"
    assert doc.file_hash == "abc123"
    assert doc.status == "uploaded"
    assert isinstance(doc.id, uuid.UUID)


async def test_get_by_id(repo: DocumentRepository) -> None:
    """get_by_id returns the correct document or None."""
    doc = await repo.create(
        file_name="a.pdf",
        original_path="/path/a.pdf",
        file_hash="hash1",
        file_type="pdf",
        file_size=100,
    )
    found = await repo.get_by_id(doc.id)
    assert found is not None
    assert found.id == doc.id

    missing = await repo.get_by_id(uuid.uuid4())
    assert missing is None


async def test_get_by_hash(repo: DocumentRepository) -> None:
    """get_by_hash finds documents by file hash."""
    doc = await repo.create(
        file_name="b.pdf",
        original_path="/path/b.pdf",
        file_hash="unique_hash",
        file_type="pdf",
        file_size=200,
    )
    found = await repo.get_by_hash("unique_hash")
    assert found is not None
    assert found.id == doc.id

    missing = await repo.get_by_hash("nonexistent")
    assert missing is None


async def test_list_all(repo: DocumentRepository) -> None:
    """list_all returns all documents with correct total count."""
    await repo.create(
        file_name="1.pdf",
        original_path="/path/1.pdf",
        file_hash="h1",
        file_type="pdf",
        file_size=100,
    )
    await repo.create(
        file_name="2.pdf",
        original_path="/path/2.pdf",
        file_hash="h2",
        file_type="pdf",
        file_size=200,
    )
    docs, total = await repo.list_all()
    assert total == 2
    assert len(docs) == 2


async def test_list_all_with_status_filter(
    repo: DocumentRepository, session: AsyncSession
) -> None:
    """list_all filters by status."""
    doc1 = await repo.create(
        file_name="1.pdf",
        original_path="/path/1.pdf",
        file_hash="h1",
        file_type="pdf",
        file_size=100,
    )
    doc1.status = "parsed"
    await repo.create(
        file_name="2.pdf",
        original_path="/path/2.pdf",
        file_hash="h2",
        file_type="pdf",
        file_size=200,
    )
    await session.flush()

    docs, total = await repo.list_all(status="parsed")
    assert total == 1
    assert docs[0].file_name == "1.pdf"


async def test_delete(repo: DocumentRepository) -> None:
    """delete removes a document and returns True."""
    doc = await repo.create(
        file_name="del.pdf",
        original_path="/path/del.pdf",
        file_hash="hdel",
        file_type="pdf",
        file_size=50,
    )
    result = await repo.delete(doc.id)
    assert result is True

    found = await repo.get_by_id(doc.id)
    assert found is None


async def test_delete_nonexistent(repo: DocumentRepository) -> None:
    """delete returns False for nonexistent document."""
    result = await repo.delete(uuid.uuid4())
    assert result is False


async def test_count_by_category(repo: DocumentRepository) -> None:
    """count_by_category returns 0 when no documents assigned."""
    count = await repo.count_by_category(uuid.uuid4())
    assert count == 0
