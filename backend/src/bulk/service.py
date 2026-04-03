"""Bulk job service: orchestrates job creation and pipeline execution."""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.bulk.pipeline import run_bulk_pipeline
from src.bulk.state import DocumentState
from src.db.models import BulkJob, Document
from src.db.repositories.bulk_jobs import BulkJobDocumentRepository, BulkJobRepository
from src.db.repositories.documents import DocumentRepository

logger = logging.getLogger(__name__)


class BulkJobService:
    """Service layer for bulk job creation and pipeline execution."""

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
        upload_dir: str = "./data/upload",
        user_id: str | None = None,
    ) -> tuple[BulkJob, list[Document]]:
        """Create a bulk job and save uploaded files to disk.

        Returns:
            Tuple of (BulkJob, list of Document records).
        """
        upload_path = Path(upload_dir)
        upload_path.mkdir(parents=True, exist_ok=True)
        documents: list[Document] = []

        for file_name, content, file_type in zip(
            file_names, file_contents, file_types, strict=True
        ):
            file_hash = hashlib.sha256(content).hexdigest()
            ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else file_type
            file_size = len(content)

            # Save file to disk
            dest = upload_path / file_name
            dest.write_bytes(content)

            # Check for duplicate by hash
            existing = await self._document_repo.get_by_hash(file_hash, user_id=user_id)
            if existing:
                documents.append(existing)
            else:
                doc = await self._document_repo.create(
                    file_name=file_name,
                    original_path=str(dest),
                    file_hash=file_hash,
                    file_type=ext,
                    file_size=file_size,
                    status="uploaded",
                    user_id=user_id,
                )
                documents.append(doc)

        job = await self._job_repo.create(
            total_documents=len(documents),
            status="pending",
            user_id=user_id,
        )

        for doc in documents:
            await self._doc_repo.create(
                job_id=job.id,
                document_id=doc.id,
                status="pending",
            )

        await self._session.commit()
        loaded_job = await self._job_repo.get_by_id(job.id)
        return loaded_job or job, documents

    async def get_job(self, job_id: uuid.UUID, user_id: str | None = None) -> BulkJob | None:
        return await self._job_repo.get_by_id(job_id, user_id=user_id)

    async def list_jobs(self, status: str | None = None, user_id: str | None = None) -> list[BulkJob]:
        return await self._job_repo.list_all(status=status, user_id=user_id)

    async def start_pipeline(
        self,
        job_id: uuid.UUID,
        categories: list[dict[str, Any]],
        extraction_fields_map: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Run the bulk pipeline for all documents in a job.

        Args:
            job_id: The bulk job ID.
            categories: All document categories for classification.
            extraction_fields_map: Map of category_id -> extraction fields.
        """
        job = await self._job_repo.get_by_id(job_id)
        if job is None:
            logger.error("Bulk job %s not found", job_id)
            return

        await self._job_repo.update_status(job_id, status="processing")
        await self._session.commit()

        doc_records = await self._doc_repo.get_by_job_id(job_id)
        logger.info(
            "Starting bulk pipeline for job %s (%d documents)",
            job_id, len(doc_records),
        )

        # Build initial states for each document
        states: list[DocumentState] = []
        doc_map: dict[str, Any] = {}

        for doc_record in doc_records:
            doc = await self._document_repo.get_by_id(doc_record.document_id)
            if doc is None:
                continue

            doc_id = str(doc.id)
            doc_map[doc_id] = doc_record

            states.append({
                "document_id": doc_id,
                "file_name": doc.file_name,
                "original_path": doc.original_path,
                "status": "pending",
                "parsed_content": "",
                "summary_text": "",
                "classification_result": {},
                "extraction_results": [],
                "categories": categories,
                "extraction_fields": [],
                "extraction_fields_map": extraction_fields_map,
                "error": None,
                "start_time_ms": time.time(),
                "end_time_ms": 0.0,
                "node_timings": {},
            })

            await self._doc_repo.update_status(doc_record.id, status="processing")

        await self._session.commit()

        # Run pipeline concurrently (10 at a time)
        results = await run_bulk_pipeline(states, concurrent_limit=10)

        # Persist results
        processed = 0
        failed = 0

        for result in results:
            doc_id = result.get("document_id", "")
            doc_record = doc_map.get(doc_id)
            if doc_record is None:
                continue

            doc = await self._document_repo.get_by_id(uuid.UUID(doc_id))
            if doc is None:
                continue

            is_failed = result.get("status") == "failed"
            elapsed = int((result.get("end_time_ms", 0) - result.get("start_time_ms", 0)) * 1000)

            if is_failed:
                await self._doc_repo.update_status(
                    doc_record.id,
                    status="failed",
                    error_message=result.get("error", "Unknown error"),
                    processing_time_ms=elapsed,
                )
                failed += 1
            else:
                await self._doc_repo.update_status(
                    doc_record.id,
                    status="completed",
                    processing_time_ms=elapsed,
                )
                processed += 1

                # Update document record with pipeline results
                parsed_path = result.get("parsed_path")
                if parsed_path:
                    doc.parsed_path = parsed_path

                cat_result = result.get("classification_result", {})
                cat_id = cat_result.get("category_id")
                if cat_id:
                    doc.document_category_id = uuid.UUID(cat_id)

                doc.status = "ingested" if result.get("chunks_created") else "extracted"

                # Save extraction results to DB
                extraction_results = result.get("extraction_results", [])
                if extraction_results:
                    from src.db.repositories.extracted_values import ExtractedValuesRepository
                    ev_repo = ExtractedValuesRepository(self._session)
                    await ev_repo.save_results(uuid.UUID(doc_id), extraction_results)

            await self._session.flush()

        await self._job_repo.update_status(
            job_id,
            status="completed" if failed == 0 else "partial_failure" if processed > 0 else "failed",
            processed_count=processed,
            failed_count=failed,
            completed_at=datetime.now(timezone.utc),
        )
        await self._session.commit()

        logger.info(
            "Bulk job %s finished: %d processed, %d failed",
            job_id, processed, failed,
        )
