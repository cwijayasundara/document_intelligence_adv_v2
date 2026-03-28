"""Tests for BulkJobRepository and BulkJobDocumentRepository."""

import uuid
from datetime import datetime, timezone

import pytest

from src.db.models import Document
from src.db.repositories.bulk_jobs import BulkJobDocumentRepository, BulkJobRepository
from tests.db_helpers import create_test_session


@pytest.fixture
async def session():
    factory = await create_test_session()
    async with factory() as session:
        yield session


@pytest.fixture
async def job_repo(session):
    return BulkJobRepository(session)


@pytest.fixture
async def doc_repo(session):
    return BulkJobDocumentRepository(session)


async def _create_document(session, file_name: str = "test.pdf") -> Document:
    """Helper to create a document for testing."""
    doc = Document(
        id=uuid.uuid4(),
        file_name=file_name,
        original_path=f"data/upload/{file_name}",
        file_hash=uuid.uuid4().hex,
        file_type="pdf",
        file_size=1024,
        status="uploaded",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(doc)
    await session.flush()
    return doc


class TestBulkJobRepository:
    """Tests for BulkJobRepository."""

    async def test_create_job(self, job_repo, session):
        """create() returns a BulkJob with pending status and correct total."""
        job = await job_repo.create(total_documents=5)

        assert job.id is not None
        assert job.status == "pending"
        assert job.total_documents == 5
        assert job.processed_count == 0
        assert job.failed_count == 0

    async def test_get_by_id_found(self, job_repo, session):
        """get_by_id() returns the job when it exists."""
        job = await job_repo.create(total_documents=3)
        await session.commit()

        found = await job_repo.get_by_id(job.id)

        assert found is not None
        assert found.id == job.id

    async def test_get_by_id_not_found(self, job_repo):
        """get_by_id() returns None for a non-existent ID."""
        result = await job_repo.get_by_id(uuid.uuid4())
        assert result is None

    async def test_list_all_returns_jobs(self, job_repo, session):
        """list_all() returns all created jobs."""
        await job_repo.create(total_documents=2)
        await job_repo.create(total_documents=3)
        await session.commit()

        jobs = await job_repo.list_all()

        assert len(jobs) == 2

    async def test_list_all_with_status_filter(self, job_repo, session):
        """list_all(status=...) filters by status."""
        job1 = await job_repo.create(total_documents=2)
        await job_repo.create(total_documents=3)
        await session.commit()

        # Update one job status
        await job_repo.update_status(job1.id, status="processing")
        await session.commit()

        pending_jobs = await job_repo.list_all(status="pending")
        processing_jobs = await job_repo.list_all(status="processing")

        assert len(pending_jobs) == 1
        assert len(processing_jobs) == 1

    async def test_update_status(self, job_repo, session):
        """update_status() changes the job status and counters."""
        job = await job_repo.create(total_documents=5)
        await session.commit()

        updated = await job_repo.update_status(
            job.id,
            status="completed",
            processed_count=4,
            failed_count=1,
            completed_at=datetime.now(timezone.utc),
        )

        assert updated is not None
        assert updated.status == "completed"
        assert updated.processed_count == 4
        assert updated.failed_count == 1
        assert updated.completed_at is not None

    async def test_update_status_not_found(self, job_repo):
        """update_status() returns None for non-existent job."""
        result = await job_repo.update_status(uuid.uuid4(), status="completed")
        assert result is None

    async def test_increment_processed(self, job_repo, session):
        """increment_processed() increments processed_count by 1."""
        job = await job_repo.create(total_documents=5)
        await session.commit()

        await job_repo.increment_processed(job.id)
        await session.commit()

        reloaded = await job_repo.get_by_id(job.id)
        assert reloaded is not None
        assert reloaded.processed_count == 1

    async def test_increment_failed(self, job_repo, session):
        """increment_failed() increments failed_count by 1."""
        job = await job_repo.create(total_documents=5)
        await session.commit()

        await job_repo.increment_failed(job.id)
        await session.commit()

        reloaded = await job_repo.get_by_id(job.id)
        assert reloaded is not None
        assert reloaded.failed_count == 1

    async def test_list_all_empty(self, job_repo):
        """list_all() returns empty list when no jobs exist."""
        jobs = await job_repo.list_all()
        assert jobs == []


class TestBulkJobDocumentRepository:
    """Tests for BulkJobDocumentRepository."""

    async def test_create_document(self, job_repo, doc_repo, session):
        """create() creates a bulk job document record."""
        job = await job_repo.create(total_documents=1)
        document = await _create_document(session)
        await session.commit()

        bjd = await doc_repo.create(
            job_id=job.id,
            document_id=document.id,
        )

        assert bjd.id is not None
        assert bjd.job_id == job.id
        assert bjd.document_id == document.id
        assert bjd.status == "pending"

    async def test_get_by_job_id(self, job_repo, doc_repo, session):
        """get_by_job_id() returns all documents for a job."""
        job = await job_repo.create(total_documents=2)
        doc1 = await _create_document(session, "file1.pdf")
        doc2 = await _create_document(session, "file2.pdf")
        await session.commit()

        await doc_repo.create(job_id=job.id, document_id=doc1.id)
        await doc_repo.create(job_id=job.id, document_id=doc2.id)
        await session.commit()

        docs = await doc_repo.get_by_job_id(job.id)
        assert len(docs) == 2

    async def test_update_status_completed(self, job_repo, doc_repo, session):
        """update_status() updates document status to completed with timing."""
        job = await job_repo.create(total_documents=1)
        document = await _create_document(session)
        await session.commit()

        bjd = await doc_repo.create(job_id=job.id, document_id=document.id)
        await session.commit()

        updated = await doc_repo.update_status(
            bjd.id,
            status="completed",
            processing_time_ms=5000,
        )

        assert updated is not None
        assert updated.status == "completed"
        assert updated.processing_time_ms == 5000
        assert updated.error_message is None

    async def test_update_status_failed(self, job_repo, doc_repo, session):
        """update_status() updates document status to failed with error message."""
        job = await job_repo.create(total_documents=1)
        document = await _create_document(session)
        await session.commit()

        bjd = await doc_repo.create(job_id=job.id, document_id=document.id)
        await session.commit()

        updated = await doc_repo.update_status(
            bjd.id,
            status="failed",
            error_message="Reducto parsing failed: corrupted PDF",
            processing_time_ms=2100,
        )

        assert updated is not None
        assert updated.status == "failed"
        assert updated.error_message == "Reducto parsing failed: corrupted PDF"
        assert updated.processing_time_ms == 2100

    async def test_count_by_status(self, job_repo, doc_repo, session):
        """count_by_status() returns correct count."""
        job = await job_repo.create(total_documents=3)
        doc1 = await _create_document(session, "a.pdf")
        doc2 = await _create_document(session, "b.pdf")
        doc3 = await _create_document(session, "c.pdf")
        await session.commit()

        bjd1 = await doc_repo.create(job_id=job.id, document_id=doc1.id)
        bjd2 = await doc_repo.create(job_id=job.id, document_id=doc2.id)
        bjd3 = await doc_repo.create(job_id=job.id, document_id=doc3.id)
        await session.commit()

        # Update statuses
        await doc_repo.update_status(bjd1.id, status="completed")
        await doc_repo.update_status(bjd2.id, status="completed")
        await doc_repo.update_status(bjd3.id, status="failed")
        await session.commit()

        completed = await doc_repo.count_by_status(job.id, "completed")
        failed = await doc_repo.count_by_status(job.id, "failed")
        pending = await doc_repo.count_by_status(job.id, "pending")

        assert completed == 2
        assert failed == 1
        assert pending == 0

    async def test_get_by_job_id_empty(self, job_repo, doc_repo, session):
        """get_by_job_id() returns empty list when no documents exist."""
        job = await job_repo.create(total_documents=0)
        await session.commit()

        docs = await doc_repo.get_by_job_id(job.id)
        assert docs == []

    async def test_update_status_not_found(self, doc_repo):
        """update_status() returns None for non-existent document."""
        result = await doc_repo.update_status(uuid.uuid4(), status="completed")
        assert result is None
