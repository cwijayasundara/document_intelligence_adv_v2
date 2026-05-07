"""Tests for ExtractionService."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from src.services.extraction_service import ExtractionService


class TestExtractionService:
    """Tests for extraction provider orchestration and caching."""

    @pytest.mark.asyncio
    async def test_extract_and_judge_delegates_to_provider(self, tmp_path) -> None:
        service = ExtractionService(extraction_dir=str(tmp_path))
        provider_results = [
            {
                "field_id": str(uuid.uuid4()),
                "field_name": "fund_name",
                "display_name": "Fund Name",
                "extracted_value": "Test Fund IV",
                "source_text": "...Test Fund IV...",
                "confidence": "high",
                "confidence_reasoning": "Explicit match in text",
                "requires_review": False,
            }
        ]
        service._run_provider = AsyncMock(return_value=provider_results)
        doc_id = uuid.uuid4()
        fields = [{"field_id": uuid.uuid4(), "field_name": "fund_name"}]

        results = await service.extract_and_judge(
            doc_id=doc_id,
            parsed_content="# Content",
            extraction_fields=fields,
            original_path="/tmp/doc.pdf",
        )

        assert results == provider_results
        service._run_provider.assert_awaited_once_with(
            doc_id=doc_id,
            parsed_content="# Content",
            extraction_fields=fields,
            original_path="/tmp/doc.pdf",
            force=False,
        )

    @pytest.mark.asyncio
    async def test_cache_hit_skips_provider(self, tmp_path) -> None:
        service = ExtractionService(extraction_dir=str(tmp_path))
        doc_id = uuid.uuid4()
        cached_results = [{"field_name": "fund_term", "extracted_value": "10 years"}]
        content_hash = service._compute_hash("# Content")
        await service._write_to_disk(doc_id, content_hash, cached_results)
        service._run_provider = AsyncMock(return_value=[])

        results = await service.extract_and_judge(
            doc_id=doc_id,
            parsed_content="# Content",
            extraction_fields=[],
        )

        assert results == cached_results
        service._run_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_force_bypasses_cache(self, tmp_path) -> None:
        service = ExtractionService(extraction_dir=str(tmp_path))
        doc_id = uuid.uuid4()
        content_hash = service._compute_hash("# Content")
        await service._write_to_disk(doc_id, content_hash, [{"field_name": "cached"}])
        fresh_results = [{"field_name": "fresh", "requires_review": False}]
        service._run_provider = AsyncMock(return_value=fresh_results)

        results = await service.extract_and_judge(
            doc_id=doc_id,
            parsed_content="# Content",
            extraction_fields=[],
            force=True,
        )

        assert results == fresh_results
        service._run_provider.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_results_are_written_to_disk(self, tmp_path) -> None:
        service = ExtractionService(extraction_dir=str(tmp_path))
        doc_id = uuid.uuid4()
        provider_results = [
            {
                "field_name": "mgmt_fee",
                "extracted_value": "2%",
                "requires_review": False,
            }
        ]
        service._run_provider = AsyncMock(return_value=provider_results)

        await service.extract_and_judge(
            doc_id=doc_id,
            parsed_content="# Content",
            extraction_fields=[],
        )

        cached = await service.get_cached(doc_id, service._compute_hash("# Content"))
        assert cached == provider_results

    def test_default_constructor_creates_extraction_dir(self, tmp_path) -> None:
        extraction_dir = tmp_path / "nested" / "extraction"

        service = ExtractionService(extraction_dir=str(extraction_dir))

        assert service._extraction_dir == extraction_dir
        assert extraction_dir.exists()
