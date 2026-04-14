"""Tests for ExtractionService."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph_nodes.schemas.extraction import (
    ExtractedField,
    ExtractionResult,
    FieldEvaluation,
    JudgeResult,
)
from src.services.extraction_service import ExtractionService


class TestExtractionService:
    """Tests for extraction + judge orchestration."""

    @pytest.mark.asyncio
    async def test_extract_and_judge_basic(self) -> None:
        """Test basic extraction and judging flow."""
        mock_extractor = MagicMock()
        mock_extractor.extract = AsyncMock(
            return_value=ExtractionResult(
                fields=[
                    ExtractedField(
                        field_name="fund_name",
                        extracted_value="Test Fund IV",
                        source_text="...Test Fund IV...",
                    )
                ]
            )
        )

        mock_judge = MagicMock()
        mock_judge.evaluate = AsyncMock(
            return_value=JudgeResult(
                evaluations=[
                    FieldEvaluation(
                        field_name="fund_name",
                        confidence="high",
                        reasoning="Explicit match in text",
                    )
                ]
            )
        )

        service = ExtractionService(extractor=mock_extractor, judge=mock_judge)

        field_id = uuid.uuid4()
        field_defs = [
            {
                "field_id": field_id,
                "field_name": "fund_name",
                "display_name": "Fund Name",
                "data_type": "string",
            }
        ]

        results = await service.extract_and_judge("# Content", field_defs)
        assert len(results) == 1
        assert results[0]["field_name"] == "fund_name"
        assert results[0]["confidence"] == "high"
        assert results[0]["requires_review"] is False
        assert results[0]["field_id"] == field_id

    @pytest.mark.asyncio
    async def test_low_confidence_requires_review(self) -> None:
        """Test that low confidence triggers requires_review."""
        mock_extractor = MagicMock()
        mock_extractor.extract = AsyncMock(
            return_value=ExtractionResult(
                fields=[
                    ExtractedField(
                        field_name="fund_term",
                        extracted_value="10 years",
                        source_text="...term...",
                    )
                ]
            )
        )

        mock_judge = MagicMock()
        mock_judge.evaluate = AsyncMock(
            return_value=JudgeResult(
                evaluations=[
                    FieldEvaluation(
                        field_name="fund_term",
                        confidence="low",
                        reasoning="Ambiguous",
                    )
                ]
            )
        )

        service = ExtractionService(extractor=mock_extractor, judge=mock_judge)

        field_defs = [
            {
                "field_id": uuid.uuid4(),
                "field_name": "fund_term",
                "display_name": "Fund Term",
            }
        ]

        results = await service.extract_and_judge("# Content", field_defs)
        assert results[0]["requires_review"] is True
        assert results[0]["confidence"] == "low"

    @pytest.mark.asyncio
    async def test_medium_confidence_no_review(self) -> None:
        """Test that medium confidence does not require review."""
        mock_extractor = MagicMock()
        mock_extractor.extract = AsyncMock(
            return_value=ExtractionResult(
                fields=[
                    ExtractedField(
                        field_name="mgmt_fee",
                        extracted_value="2%",
                        source_text="...2% fee...",
                    )
                ]
            )
        )

        mock_judge = MagicMock()
        mock_judge.evaluate = AsyncMock(
            return_value=JudgeResult(
                evaluations=[
                    FieldEvaluation(
                        field_name="mgmt_fee",
                        confidence="medium",
                        reasoning="Partially clear",
                    )
                ]
            )
        )

        service = ExtractionService(extractor=mock_extractor, judge=mock_judge)

        results = await service.extract_and_judge(
            "# Content",
            [{"field_id": uuid.uuid4(), "field_name": "mgmt_fee", "display_name": "Fee"}],
        )
        assert results[0]["requires_review"] is False

    @pytest.mark.asyncio
    async def test_empty_fields(self) -> None:
        """Test extraction with no fields."""
        mock_extractor = MagicMock()
        mock_extractor.extract = AsyncMock(return_value=ExtractionResult(fields=[]))

        mock_judge = MagicMock()
        mock_judge.evaluate = AsyncMock(return_value=JudgeResult(evaluations=[]))

        service = ExtractionService(extractor=mock_extractor, judge=mock_judge)

        results = await service.extract_and_judge("# Content", [])
        assert results == []

    @pytest.mark.asyncio
    async def test_default_constructor(self) -> None:
        """Test default constructor creates real subagents."""
        with (
            patch("src.graph_nodes.extractor.create_deep_agent", return_value=MagicMock()),
            patch("src.graph_nodes.judge.create_deep_agent", return_value=MagicMock()),
        ):
            service = ExtractionService()
            assert service._extractor is not None
            assert service._judge is not None
