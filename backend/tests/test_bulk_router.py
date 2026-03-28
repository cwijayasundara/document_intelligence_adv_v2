"""Tests for the bulk processing API router endpoints."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.app import create_app
from src.api.dependencies import get_session


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def app(mock_session: AsyncMock) -> FastAPI:
    application = create_app(database_url="")

    async def override_session():
        yield mock_session

    application.dependency_overrides[get_session] = override_session
    return application


@pytest.fixture
async def client(app: FastAPI):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _make_mock_document(
    doc_id: uuid.UUID | None = None,
    file_name: str = "test.pdf",
) -> MagicMock:
    """Create a mock Document object."""
    mock = MagicMock()
    mock.id = doc_id or uuid.uuid4()
    mock.file_name = file_name
    mock.original_path = f"data/upload/{file_name}"
    mock.file_hash = "abc123"
    mock.file_type = "pdf"
    mock.file_size = 1024
    mock.status = "uploaded"
    mock.created_at = datetime(2026, 3, 28, tzinfo=timezone.utc)
    mock.updated_at = datetime(2026, 3, 28, tzinfo=timezone.utc)
    return mock


def _make_mock_job(
    job_id: uuid.UUID | None = None,
    status: str = "pending",
    total: int = 2,
    processed: int = 0,
    failed: int = 0,
    documents: list | None = None,
) -> MagicMock:
    """Create a mock BulkJob object."""
    mock = MagicMock()
    mock.id = job_id or uuid.uuid4()
    mock.status = status
    mock.total_documents = total
    mock.processed_count = processed
    mock.failed_count = failed
    mock.created_at = datetime(2026, 3, 28, tzinfo=timezone.utc)
    mock.completed_at = None
    mock.documents = documents or []
    return mock


def _make_mock_bulk_job_doc(
    document_id: uuid.UUID | None = None,
    file_name: str = "test.pdf",
    status: str = "pending",
    error_message: str | None = None,
    processing_time_ms: int | None = None,
) -> MagicMock:
    """Create a mock BulkJobDocument object."""
    mock = MagicMock()
    mock.id = uuid.uuid4()
    mock.document_id = document_id or uuid.uuid4()
    mock.status = status
    mock.error_message = error_message
    mock.processing_time_ms = processing_time_ms
    # Mock the document relationship for file_name access
    mock.document = MagicMock()
    mock.document.file_name = file_name
    return mock


@patch("src.api.routers.bulk.BulkJobService")
async def test_bulk_upload_creates_job(
    MockService: MagicMock,
    client: AsyncClient,
) -> None:
    """POST /bulk/upload creates a bulk job with uploaded files."""
    doc1 = _make_mock_document(file_name="doc1.pdf")
    doc2 = _make_mock_document(file_name="doc2.pdf")
    mock_job = _make_mock_job(total=2)

    instance = MockService.return_value
    instance.create_job = AsyncMock(return_value=(mock_job, [doc1, doc2]))

    response = await client.post(
        "/api/v1/bulk/upload",
        files=[
            ("files", ("doc1.pdf", b"content1", "application/pdf")),
            ("files", ("doc2.pdf", b"content2", "application/pdf")),
        ],
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["total_documents"] == 2
    assert len(data["documents"]) == 2


@patch("src.api.routers.bulk.BulkJobService")
async def test_bulk_upload_no_files(
    MockService: MagicMock,
    client: AsyncClient,
) -> None:
    """POST /bulk/upload returns 422 when no files provided."""
    response = await client.post(
        "/api/v1/bulk/upload",
        files=[],
    )

    assert response.status_code == 422


@patch("src.api.routers.bulk.BulkJobService")
async def test_bulk_upload_invalid_file_type(
    MockService: MagicMock,
    client: AsyncClient,
) -> None:
    """POST /bulk/upload returns 422 for invalid file types."""
    response = await client.post(
        "/api/v1/bulk/upload",
        files=[
            ("files", ("malware.exe", b"content", "application/octet-stream")),
        ],
    )

    assert response.status_code == 422
    assert "not allowed" in response.json()["detail"]


@patch("src.api.routers.bulk.BulkJobService")
async def test_list_bulk_jobs(
    MockService: MagicMock,
    client: AsyncClient,
) -> None:
    """GET /bulk/jobs returns list of bulk jobs."""
    job1 = _make_mock_job(status="completed", total=5, processed=4, failed=1)
    job2 = _make_mock_job(status="processing", total=3)

    instance = MockService.return_value
    instance.list_jobs = AsyncMock(return_value=[job1, job2])

    response = await client.get("/api/v1/bulk/jobs")

    assert response.status_code == 200
    data = response.json()
    assert len(data["jobs"]) == 2
    assert data["jobs"][0]["status"] == "completed"
    assert data["jobs"][0]["total_documents"] == 5


@patch("src.api.routers.bulk.BulkJobService")
async def test_list_bulk_jobs_with_status_filter(
    MockService: MagicMock,
    client: AsyncClient,
) -> None:
    """GET /bulk/jobs?status_filter=processing filters jobs."""
    job = _make_mock_job(status="processing")

    instance = MockService.return_value
    instance.list_jobs = AsyncMock(return_value=[job])

    response = await client.get("/api/v1/bulk/jobs?status_filter=processing")

    assert response.status_code == 200
    data = response.json()
    assert len(data["jobs"]) == 1
    instance.list_jobs.assert_called_once_with(status="processing")


@patch("src.api.routers.bulk.BulkJobService")
async def test_list_bulk_jobs_empty(
    MockService: MagicMock,
    client: AsyncClient,
) -> None:
    """GET /bulk/jobs returns empty list when no jobs exist."""
    instance = MockService.return_value
    instance.list_jobs = AsyncMock(return_value=[])

    response = await client.get("/api/v1/bulk/jobs")

    assert response.status_code == 200
    assert response.json()["jobs"] == []


@patch("src.api.routers.bulk.BulkJobService")
async def test_get_bulk_job_detail(
    MockService: MagicMock,
    client: AsyncClient,
) -> None:
    """GET /bulk/jobs/:id returns job details with document breakdown."""
    job_id = uuid.uuid4()
    doc1_id = uuid.uuid4()
    doc2_id = uuid.uuid4()

    bulk_docs = [
        _make_mock_bulk_job_doc(
            document_id=doc1_id,
            file_name="doc1.pdf",
            status="completed",
            processing_time_ms=12340,
        ),
        _make_mock_bulk_job_doc(
            document_id=doc2_id,
            file_name="doc2.pdf",
            status="failed",
            error_message="Reducto parsing failed: corrupted PDF",
            processing_time_ms=2100,
        ),
    ]

    mock_job = _make_mock_job(
        job_id=job_id,
        status="completed",
        total=2,
        processed=1,
        failed=1,
        documents=bulk_docs,
    )

    instance = MockService.return_value
    instance.get_job = AsyncMock(return_value=mock_job)

    response = await client.get(f"/api/v1/bulk/jobs/{job_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(job_id)
    assert data["status"] == "completed"
    assert data["total_documents"] == 2
    assert data["processed_count"] == 1
    assert data["failed_count"] == 1
    assert len(data["documents"]) == 2

    # Check completed doc
    completed_doc = data["documents"][0]
    assert completed_doc["status"] == "completed"
    assert completed_doc["processing_time_ms"] == 12340

    # Check failed doc
    failed_doc = data["documents"][1]
    assert failed_doc["status"] == "failed"
    assert "corrupted PDF" in failed_doc["error_message"]


@patch("src.api.routers.bulk.BulkJobService")
async def test_get_bulk_job_not_found(
    MockService: MagicMock,
    client: AsyncClient,
) -> None:
    """GET /bulk/jobs/:id returns 404 for non-existent job."""
    instance = MockService.return_value
    instance.get_job = AsyncMock(return_value=None)

    response = await client.get(f"/api/v1/bulk/jobs/{uuid.uuid4()}")

    assert response.status_code == 404


@patch("src.api.routers.bulk.BulkJobService")
async def test_bulk_upload_mixed_file_types(
    MockService: MagicMock,
    client: AsyncClient,
) -> None:
    """POST /bulk/upload handles mixed valid file types."""
    doc1 = _make_mock_document(file_name="report.pdf")
    doc2 = _make_mock_document(file_name="data.xlsx")
    mock_job = _make_mock_job(total=2)

    instance = MockService.return_value
    instance.create_job = AsyncMock(return_value=(mock_job, [doc1, doc2]))

    response = await client.post(
        "/api/v1/bulk/upload",
        files=[
            ("files", ("report.pdf", b"content1", "application/pdf")),
            (
                "files",
                (
                    "data.xlsx",
                    b"content2",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            ),
        ],
    )

    assert response.status_code == 201


@patch("src.api.routers.bulk.BulkJobService")
async def test_bulk_upload_single_file(
    MockService: MagicMock,
    client: AsyncClient,
) -> None:
    """POST /bulk/upload works with a single file."""
    doc = _make_mock_document(file_name="single.pdf")
    mock_job = _make_mock_job(total=1)

    instance = MockService.return_value
    instance.create_job = AsyncMock(return_value=(mock_job, [doc]))

    response = await client.post(
        "/api/v1/bulk/upload",
        files=[
            ("files", ("single.pdf", b"content", "application/pdf")),
        ],
    )

    assert response.status_code == 201
    data = response.json()
    assert data["total_documents"] == 1
    assert len(data["documents"]) == 1
