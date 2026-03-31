"""Bulk job repository with async CRUD operations."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import BulkJob, BulkJobDocument


class BulkJobRepository:
    """Async repository for bulk job CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        total_documents: int,
        status: str = "pending",
        user_id: str | None = None,
    ) -> BulkJob:
        """Create a new bulk job record."""
        job = BulkJob(
            id=uuid.uuid4(),
            status=status,
            total_documents=total_documents,
            processed_count=0,
            failed_count=0,
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(job)
        await self._session.flush()
        return job

    async def get_by_id(
        self,
        job_id: uuid.UUID,
        user_id: str | None = None,
    ) -> BulkJob | None:
        """Get a bulk job by ID with its documents eagerly loaded."""
        stmt = select(BulkJob).where(BulkJob.id == job_id).options(selectinload(BulkJob.documents))
        if user_id is not None:
            stmt = stmt.where(BulkJob.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        status: str | None = None,
        user_id: str | None = None,
    ) -> list[BulkJob]:
        """List all bulk jobs with optional status filter."""
        stmt = select(BulkJob).order_by(BulkJob.created_at.desc())

        if user_id is not None:
            stmt = stmt.where(BulkJob.user_id == user_id)
        if status is not None:
            stmt = stmt.where(BulkJob.status == status)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        job_id: uuid.UUID,
        status: str,
        processed_count: int | None = None,
        failed_count: int | None = None,
        completed_at: datetime | None = None,
    ) -> BulkJob | None:
        """Update the status and counters of a bulk job."""
        values: dict = {"status": status}
        if processed_count is not None:
            values["processed_count"] = processed_count
        if failed_count is not None:
            values["failed_count"] = failed_count
        if completed_at is not None:
            values["completed_at"] = completed_at

        stmt = update(BulkJob).where(BulkJob.id == job_id).values(**values)
        await self._session.execute(stmt)
        await self._session.flush()

        return await self.get_by_id(job_id)

    async def increment_processed(self, job_id: uuid.UUID) -> None:
        """Increment the processed_count by 1."""
        stmt = (
            update(BulkJob)
            .where(BulkJob.id == job_id)
            .values(processed_count=BulkJob.processed_count + 1)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def increment_failed(self, job_id: uuid.UUID) -> None:
        """Increment the failed_count by 1."""
        stmt = (
            update(BulkJob)
            .where(BulkJob.id == job_id)
            .values(failed_count=BulkJob.failed_count + 1)
        )
        await self._session.execute(stmt)
        await self._session.flush()


class BulkJobDocumentRepository:
    """Async repository for bulk job document CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        job_id: uuid.UUID,
        document_id: uuid.UUID,
        status: str = "pending",
    ) -> BulkJobDocument:
        """Create a new bulk job document record."""
        doc = BulkJobDocument(
            id=uuid.uuid4(),
            job_id=job_id,
            document_id=document_id,
            status=status,
        )
        self._session.add(doc)
        await self._session.flush()
        return doc

    async def get_by_job_id(self, job_id: uuid.UUID) -> list[BulkJobDocument]:
        """Get all documents for a specific bulk job."""
        stmt = select(BulkJobDocument).where(BulkJobDocument.job_id == job_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        doc_id: uuid.UUID,
        status: str,
        error_message: str | None = None,
        processing_time_ms: int | None = None,
    ) -> BulkJobDocument | None:
        """Update the status of a bulk job document."""
        values: dict = {"status": status}
        if error_message is not None:
            values["error_message"] = error_message
        if processing_time_ms is not None:
            values["processing_time_ms"] = processing_time_ms

        stmt = update(BulkJobDocument).where(BulkJobDocument.id == doc_id).values(**values)
        await self._session.execute(stmt)
        await self._session.flush()

        result = await self._session.execute(
            select(BulkJobDocument).where(BulkJobDocument.id == doc_id)
        )
        return result.scalar_one_or_none()

    async def count_by_status(self, job_id: uuid.UUID, status: str) -> int:
        """Count documents with a given status in a job."""
        stmt = (
            select(func.count())
            .select_from(BulkJobDocument)
            .where(
                BulkJobDocument.job_id == job_id,
                BulkJobDocument.status == status,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0
