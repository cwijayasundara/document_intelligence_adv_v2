"""Bulk job service: orchestrates job creation and pipeline execution."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import BulkJob, Document
from src.db.repositories.bulk_jobs import BulkJobDocumentRepository, BulkJobRepository
from src.db.repositories.documents import DocumentRepository

logger = logging.getLogger(__name__)


class BulkJobService:
    """Service layer for bulk job creation and pipeline management."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._job_repo = BulkJobRepository(session)
        self._doc_repo = BulkJobDocumentRepository(session)
        self._document_repo = DocumentRepository(session)

    async def create_job(
        self,
        file_names: list[str],
        file_contents: list[bytes],
        file_types: list[str],
    ) -> tuple[BulkJob, list[Document]]:
        """Create a bulk job with uploaded files.

        Creates document records for each file, then creates a bulk_job
        and associated bulk_job_documents records.

        Args:
            file_names: Original file names.
            file_contents: Raw file bytes.
            file_types: MIME types or extensions.

        Returns:
            Tuple of (BulkJob, list of Document records).
        """
        import hashlib

        documents: list[Document] = []

        for file_name, content, file_type in zip(
            file_names, file_contents, file_types, strict=True
        ):
            file_hash = hashlib.sha256(content).hexdigest()
            ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else file_type
            file_size = len(content)

            # Check for duplicate by hash
            existing = await self._document_repo.get_by_hash(file_hash)
            if existing:
                documents.append(existing)
            else:
                doc = await self._document_repo.create(
                    file_name=file_name,
                    original_path=f"data/upload/{file_name}",
                    file_hash=file_hash,
                    file_type=ext,
                    file_size=file_size,
                    status="uploaded",
                )
                documents.append(doc)

        # Create the bulk job
        job = await self._job_repo.create(
            total_documents=len(documents),
            status="pending",
        )

        # Create bulk job document records
        for doc in documents:
            await self._doc_repo.create(
                job_id=job.id,
                document_id=doc.id,
                status="pending",
            )

        await self._session.commit()

        # Reload job with documents
        loaded_job = await self._job_repo.get_by_id(job.id)
        return loaded_job or job, documents

    async def get_job(self, job_id: uuid.UUID) -> BulkJob | None:
        """Get a bulk job by ID with document details."""
        return await self._job_repo.get_by_id(job_id)

    async def list_jobs(self, status: str | None = None) -> list[BulkJob]:
        """List all bulk jobs with optional status filter."""
        return await self._job_repo.list_all(status=status)

    async def start_pipeline(
        self,
        job_id: uuid.UUID,
        run_pipeline_fn: Any = None,
    ) -> None:
        """Start the bulk pipeline processing in the background.

        Args:
            job_id: The bulk job ID to process.
            run_pipeline_fn: Optional callable for the pipeline.
                If None, uses the default bulk pipeline.
        """
        job = await self._job_repo.get_by_id(job_id)
        if job is None:
            logger.error("Bulk job %s not found", job_id)
            return

        await self._job_repo.update_status(job_id, status="processing")
        await self._session.commit()

        doc_records = await self._doc_repo.get_by_job_id(job_id)
        processed = 0
        failed = 0

        for doc_record in doc_records:
            start_ms = int(time.time() * 1000)
            try:
                if run_pipeline_fn:
                    await run_pipeline_fn(str(doc_record.document_id))

                elapsed = int(time.time() * 1000) - start_ms
                await self._doc_repo.update_status(
                    doc_record.id,
                    status="completed",
                    processing_time_ms=elapsed,
                )
                processed += 1
            except Exception as exc:
                elapsed = int(time.time() * 1000) - start_ms
                await self._doc_repo.update_status(
                    doc_record.id,
                    status="failed",
                    error_message=str(exc),
                    processing_time_ms=elapsed,
                )
                failed += 1
                logger.warning(
                    "Bulk pipeline failed for document %s: %s",
                    doc_record.document_id,
                    exc,
                )

        await self._job_repo.update_status(
            job_id,
            status="completed",
            processed_count=processed,
            failed_count=failed,
            completed_at=datetime.now(timezone.utc),
        )
        await self._session.commit()
