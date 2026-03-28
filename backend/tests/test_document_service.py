"""Tests for DocumentService: upload, dedup, delete."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.document_service import DocumentService
from src.storage.local import LocalStorage
from tests.db_helpers import create_test_session


@pytest.fixture
async def session():
    factory = await create_test_session()
    async with factory() as session:
        yield session


@pytest.fixture
def storage(tmp_path) -> LocalStorage:
    upload_dir = tmp_path / "upload"
    parsed_dir = tmp_path / "parsed"
    return LocalStorage(str(upload_dir), str(parsed_dir))


@pytest.fixture
def service(session: AsyncSession, storage: LocalStorage) -> DocumentService:
    return DocumentService(session, storage)


async def test_upload_creates_document(service: DocumentService, storage: LocalStorage) -> None:
    """Upload saves file and creates document record."""
    content = b"PDF content here"
    doc, is_dup = await service.upload("test.pdf", content)

    assert is_dup is False
    assert doc.file_name == "test.pdf"
    assert doc.file_type == "pdf"
    assert doc.file_size == len(content)
    assert doc.status == "uploaded"
    assert storage.file_exists(doc.original_path)


async def test_upload_dedup_returns_existing(
    service: DocumentService,
) -> None:
    """Upload with identical content returns existing doc as duplicate."""
    content = b"Same content"
    doc1, is_dup1 = await service.upload("first.pdf", content)
    doc2, is_dup2 = await service.upload("second.pdf", content)

    assert is_dup1 is False
    assert is_dup2 is True
    assert doc2.id == doc1.id


async def test_upload_rejects_invalid_type(service: DocumentService) -> None:
    """Upload raises ValueError for unsupported file types."""
    with pytest.raises(ValueError, match="not allowed"):
        await service.upload("test.exe", b"bad content")


async def test_get_document(service: DocumentService) -> None:
    """get_document returns the uploaded document."""
    doc, _ = await service.upload("get.pdf", b"content")
    found = await service.get_document(doc.id)
    assert found is not None
    assert found.id == doc.id


async def test_get_document_not_found(service: DocumentService) -> None:
    """get_document returns None for missing ID."""
    result = await service.get_document(uuid.uuid4())
    assert result is None


async def test_list_documents(service: DocumentService) -> None:
    """list_documents returns all uploaded documents."""
    await service.upload("a.pdf", b"aaa")
    await service.upload("b.pdf", b"bbb")
    docs, total = await service.list_documents()
    assert total == 2
    assert len(docs) == 2


async def test_delete_document(service: DocumentService, storage: LocalStorage) -> None:
    """delete_document removes record and file."""
    doc, _ = await service.upload("del.pdf", b"delete me")
    path = doc.original_path

    result = await service.delete_document(doc.id)
    assert result is True
    assert not storage.file_exists(path)


async def test_delete_nonexistent(service: DocumentService) -> None:
    """delete_document returns False for missing document."""
    result = await service.delete_document(uuid.uuid4())
    assert result is False


async def test_extract_extension() -> None:
    """_extract_extension returns lowercase extension."""
    assert DocumentService._extract_extension("test.PDF") == "pdf"
    assert DocumentService._extract_extension("doc.docx") == "docx"
    assert DocumentService._extract_extension("image.PNG") == "png"
