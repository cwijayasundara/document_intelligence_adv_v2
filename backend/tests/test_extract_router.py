"""Tests for extraction API router endpoints."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app
from src.api.dependencies import get_session


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def app(mock_session) -> FastAPI:
    application = create_app(database_url="")

    async def _override_session():
        yield mock_session

    application.dependency_overrides[get_session] = _override_session
    return application


@pytest.fixture
async def client(app: FastAPI):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestExtractHelpers:
    """Tests for extract router helper functions."""

    def test_get_extraction_service_singleton(self) -> None:
        import src.api.routers.extract as extract_mod

        extract_mod._extraction_service = None  # reset singleton
        with (
            patch("src.agents.extractor.create_deep_agent", return_value=MagicMock()),
            patch("src.agents.judge.create_deep_agent", return_value=MagicMock()),
        ):
            from src.api.routers.extract import _get_extraction_service

            svc1 = _get_extraction_service()
            svc2 = _get_extraction_service()
            assert svc1 is svc2
        extract_mod._extraction_service = None  # cleanup

    @pytest.mark.asyncio
    async def test_load_extraction_fields_no_category(self) -> None:
        from src.api.routers.extract import _load_extraction_fields

        session = AsyncMock()
        result = await _load_extraction_fields(session, None)
        assert result == []

    @pytest.mark.asyncio
    async def test_load_extraction_fields_no_schema(self) -> None:
        from src.api.routers.extract import _load_extraction_fields

        with patch("src.api.routers.extract.ExtractionSchemaRepository") as mock_schema_cls:
            mock_schema_repo = MagicMock()
            mock_schema_repo.get_latest_for_category = AsyncMock(return_value=None)
            mock_schema_cls.return_value = mock_schema_repo

            session = AsyncMock()
            result = await _load_extraction_fields(session, uuid.uuid4())
            assert result == []

    @pytest.mark.asyncio
    async def test_load_extraction_fields_with_fields(self) -> None:
        from src.api.routers.extract import _load_extraction_fields

        schema_id = uuid.uuid4()
        mock_schema = MagicMock()
        mock_schema.id = schema_id

        mock_field = MagicMock()
        mock_field.id = uuid.uuid4()
        mock_field.field_name = "fund_name"
        mock_field.display_name = "Fund Name"
        mock_field.description = "Name of the fund"
        mock_field.data_type = "string"
        mock_field.examples = "Fund IV"

        with (
            patch("src.api.routers.extract.ExtractionSchemaRepository") as mock_schema_cls,
            patch("src.api.routers.extract.ExtractionFieldRepository") as mock_field_cls,
        ):
            mock_schema_repo = MagicMock()
            mock_schema_repo.get_latest_for_category = AsyncMock(return_value=mock_schema)
            mock_schema_cls.return_value = mock_schema_repo

            mock_field_repo = MagicMock()
            mock_field_repo.get_fields_for_schema = AsyncMock(return_value=[mock_field])
            mock_field_cls.return_value = mock_field_repo

            session = AsyncMock()
            result = await _load_extraction_fields(session, uuid.uuid4())
            assert len(result) == 1
            assert result[0]["field_name"] == "fund_name"


class TestExtractRouter:
    """Tests for extraction API endpoints."""

    @pytest.mark.asyncio
    async def test_extract_not_found(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        with patch("src.api.routers.extract.DocumentRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            resp = await client.post(f"/api/v1/extract/{doc_id}")
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_extract_invalid_transition(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.status = "uploaded"

        with patch("src.api.routers.extract.DocumentRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
            mock_repo_cls.return_value = mock_repo

            resp = await client.post(f"/api/v1/extract/{doc_id}")
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_extract_no_parsed_content(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.status = "classified"
        mock_doc.parsed_path = None

        with patch("src.api.routers.extract.DocumentRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
            mock_repo_cls.return_value = mock_repo

            resp = await client.post(f"/api/v1/extract/{doc_id}")
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_extract_success(self, client: AsyncClient, tmp_path) -> None:
        doc_id = uuid.uuid4()
        field_id = uuid.uuid4()
        ev_id = uuid.uuid4()
        parsed_file = tmp_path / "test.md"
        parsed_file.write_text("# Test Document Content")

        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.status = "classified"
        mock_doc.parsed_path = str(parsed_file)
        mock_doc.document_category_id = uuid.uuid4()

        mock_saved = MagicMock()
        mock_saved.id = ev_id

        with (
            patch("src.api.routers.extract.DocumentRepository") as mock_repo_cls,
            patch("src.api.routers.extract._load_extraction_fields") as mock_load,
            patch("src.api.routers.extract._get_extraction_service") as mock_svc,
            patch("src.api.routers.extract.ExtractedValuesRepository") as mock_ev_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
            mock_repo_cls.return_value = mock_repo

            mock_load.return_value = [
                {
                    "field_id": field_id,
                    "field_name": "fund_name",
                    "display_name": "Fund Name",
                    "data_type": "string",
                }
            ]

            service = MagicMock()
            service.extract_and_judge = AsyncMock(
                return_value=[
                    {
                        "field_id": field_id,
                        "field_name": "fund_name",
                        "display_name": "Fund Name",
                        "extracted_value": "Test Fund",
                        "source_text": "...Test Fund...",
                        "confidence": "high",
                        "confidence_reasoning": "Clear",
                        "requires_review": False,
                    }
                ]
            )
            mock_svc.return_value = service

            mock_ev_repo = MagicMock()
            mock_ev_repo.save_results = AsyncMock(return_value=[mock_saved])
            mock_ev_cls.return_value = mock_ev_repo

            resp = await client.post(f"/api/v1/extract/{doc_id}")
            assert resp.status_code == 201
            data = resp.json()
            assert data["status"] == "extracted"
            assert len(data["results"]) == 1
            assert data["requires_review_count"] == 0

    @pytest.mark.asyncio
    async def test_get_results_not_found(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        with patch("src.api.routers.extract.DocumentRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            resp = await client.get(f"/api/v1/extract/{doc_id}/results")
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_results_no_values(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        mock_doc = MagicMock()
        mock_doc.id = doc_id

        with (
            patch("src.api.routers.extract.DocumentRepository") as mock_repo_cls,
            patch("src.api.routers.extract.ExtractedValuesRepository") as mock_ev_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
            mock_repo_cls.return_value = mock_repo

            mock_ev_repo = MagicMock()
            mock_ev_repo.get_by_document_id = AsyncMock(return_value=[])
            mock_ev_cls.return_value = mock_ev_repo

            resp = await client.get(f"/api/v1/extract/{doc_id}/results")
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_results_success(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        mock_doc = MagicMock()
        mock_doc.id = doc_id

        mock_field = MagicMock()
        mock_field.field_name = "fund_name"
        mock_field.display_name = "Fund Name"

        mock_ev = MagicMock()
        mock_ev.id = uuid.uuid4()
        mock_ev.field = mock_field
        mock_ev.extracted_value = "Test Fund"
        mock_ev.source_text = "source"
        mock_ev.confidence = "high"
        mock_ev.confidence_reasoning = "Clear"
        mock_ev.requires_review = False
        mock_ev.reviewed = False

        with (
            patch("src.api.routers.extract.DocumentRepository") as mock_repo_cls,
            patch("src.api.routers.extract.ExtractedValuesRepository") as mock_ev_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
            mock_repo_cls.return_value = mock_repo

            mock_ev_repo = MagicMock()
            mock_ev_repo.get_by_document_id = AsyncMock(return_value=[mock_ev])
            mock_ev_cls.return_value = mock_ev_repo

            resp = await client.get(f"/api/v1/extract/{doc_id}/results")
            assert resp.status_code == 200
            data = resp.json()
            assert data["all_reviewed"] is True

    @pytest.mark.asyncio
    async def test_update_results_doc_not_found(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        with patch("src.api.routers.extract.DocumentRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            resp = await client.put(
                f"/api/v1/extract/{doc_id}/results",
                json={"updates": []},
            )
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_results_review_gate_fail(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        mock_doc = MagicMock()
        mock_doc.id = doc_id

        with (
            patch("src.api.routers.extract.DocumentRepository") as mock_repo_cls,
            patch("src.api.routers.extract.ExtractedValuesRepository") as mock_ev_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
            mock_repo_cls.return_value = mock_repo

            mock_ev_repo = MagicMock()
            mock_ev_repo.update_values = AsyncMock(return_value=0)
            mock_ev_repo.get_unreviewed_fields = AsyncMock(
                return_value=["fund_term", "governing_law"]
            )
            mock_ev_cls.return_value = mock_ev_repo

            resp = await client.put(
                f"/api/v1/extract/{doc_id}/results",
                json={"updates": []},
            )
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_results_success(self, client: AsyncClient) -> None:
        doc_id = uuid.uuid4()
        field_id = uuid.uuid4()
        mock_doc = MagicMock()
        mock_doc.id = doc_id

        with (
            patch("src.api.routers.extract.DocumentRepository") as mock_repo_cls,
            patch("src.api.routers.extract.ExtractedValuesRepository") as mock_ev_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
            mock_repo_cls.return_value = mock_repo

            mock_ev_repo = MagicMock()
            mock_ev_repo.update_values = AsyncMock(return_value=1)
            mock_ev_repo.get_unreviewed_fields = AsyncMock(return_value=[])
            mock_ev_cls.return_value = mock_ev_repo

            resp = await client.put(
                f"/api/v1/extract/{doc_id}/results",
                json={
                    "updates": [
                        {
                            "field_id": str(field_id),
                            "extracted_value": "Updated",
                            "reviewed": True,
                        }
                    ]
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["all_reviewed"] is True
            assert data["can_proceed"] is True
