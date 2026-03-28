"""Tests for BulkJobService."""

import uuid
from unittest.mock import AsyncMock

import pytest

from src.bulk.service import BulkJobService
from tests.db_helpers import create_test_session


@pytest.fixture
async def session():
    factory = await create_test_session()
    async with factory() as session:
        yield session


@pytest.fixture
def service(session):
    return BulkJobService(session)


class TestBulkJobServiceCreate:
    """Tests for BulkJobService.create_job()."""

    async def test_create_job_with_files(self, service, session):
        """create_job() creates documents, a job, and links them."""
        file_names = ["doc1.pdf", "doc2.pdf"]
        file_contents = [b"content1", b"content2"]
        file_types = ["pdf", "pdf"]

        job, documents = await service.create_job(file_names, file_contents, file_types)

        assert job is not None
        assert job.status == "pending"
        assert job.total_documents == 2
        assert len(documents) == 2
        assert documents[0].file_name == "doc1.pdf"
        assert documents[1].file_name == "doc2.pdf"

    async def test_create_job_dedup_by_hash(self, service, session):
        """create_job() reuses existing documents with matching hash."""
        content = b"identical content"
        file_names = ["doc1.pdf"]
        file_contents = [content]
        file_types = ["pdf"]

        # Create first job
        job1, docs1 = await service.create_job(file_names, file_contents, file_types)

        # Create second job with same content but different name
        job2, docs2 = await service.create_job(["doc1_copy.pdf"], [content], ["pdf"])

        # Should reuse the same document
        assert docs1[0].id == docs2[0].id

    async def test_create_job_extracts_extension(self, service, session):
        """create_job() extracts file extension from filename."""
        job, documents = await service.create_job(["report.docx"], [b"docx content"], ["docx"])

        assert documents[0].file_type == "docx"


class TestBulkJobServiceQuery:
    """Tests for BulkJobService query methods."""

    async def test_get_job_found(self, service, session):
        """get_job() returns job when it exists."""
        job, _ = await service.create_job(["test.pdf"], [b"data"], ["pdf"])

        found = await service.get_job(job.id)

        assert found is not None
        assert found.id == job.id

    async def test_get_job_not_found(self, service):
        """get_job() returns None for non-existent job."""
        result = await service.get_job(uuid.uuid4())
        assert result is None

    async def test_list_jobs_returns_all(self, service, session):
        """list_jobs() returns all created jobs."""
        await service.create_job(["a.pdf"], [b"a"], ["pdf"])
        await service.create_job(["b.pdf"], [b"b"], ["pdf"])

        jobs = await service.list_jobs()

        assert len(jobs) == 2

    async def test_list_jobs_with_status_filter(self, service, session):
        """list_jobs(status=...) filters by status."""
        await service.create_job(["a.pdf"], [b"a"], ["pdf"])

        pending = await service.list_jobs(status="pending")
        processing = await service.list_jobs(status="processing")

        assert len(pending) == 1
        assert len(processing) == 0

    async def test_list_jobs_empty(self, service):
        """list_jobs() returns empty list when no jobs exist."""
        jobs = await service.list_jobs()
        assert jobs == []


class TestBulkJobServicePipeline:
    """Tests for BulkJobService.start_pipeline()."""

    async def test_start_pipeline_processes_documents(self, service, session):
        """start_pipeline() runs pipeline and updates statuses."""
        job, docs = await service.create_job(
            ["doc1.pdf", "doc2.pdf"],
            [b"content1", b"content2"],
            ["pdf", "pdf"],
        )

        mock_pipeline = AsyncMock()
        await service.start_pipeline(job.id, run_pipeline_fn=mock_pipeline)

        # Verify pipeline was called for each document
        assert mock_pipeline.call_count == 2

        # Verify job is completed
        updated_job = await service.get_job(job.id)
        assert updated_job is not None
        assert updated_job.status == "completed"
        assert updated_job.processed_count == 2
        assert updated_job.failed_count == 0

    async def test_start_pipeline_handles_failures(self, service, session):
        """start_pipeline() records failures with error messages."""
        job, docs = await service.create_job(
            ["good.pdf", "bad.pdf"],
            [b"good", b"bad"],
            ["pdf", "pdf"],
        )

        call_count = 0

        async def mock_pipeline(doc_id: str):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("Reducto parsing failed: corrupted PDF")

        await service.start_pipeline(job.id, run_pipeline_fn=mock_pipeline)

        updated_job = await service.get_job(job.id)
        assert updated_job is not None
        assert updated_job.status == "completed"
        assert updated_job.processed_count == 1
        assert updated_job.failed_count == 1

    async def test_start_pipeline_nonexistent_job(self, service, session):
        """start_pipeline() returns early for non-existent job."""
        # Should not raise
        await service.start_pipeline(uuid.uuid4())

    async def test_start_pipeline_updates_to_processing(self, service, session):
        """start_pipeline() sets job status to processing before running."""
        job, _ = await service.create_job(["test.pdf"], [b"data"], ["pdf"])

        statuses_seen = []

        async def mock_pipeline(doc_id: str):
            # During pipeline execution, check job status
            check_job = await service.get_job(job.id)
            if check_job:
                statuses_seen.append(check_job.status)

        await service.start_pipeline(job.id, run_pipeline_fn=mock_pipeline)

        assert "processing" in statuses_seen
