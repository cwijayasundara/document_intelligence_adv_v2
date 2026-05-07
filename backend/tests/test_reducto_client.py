"""Tests for the Reducto client."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.parser.reducto import ReductoClient, ReductoParseError


class TestReductoClient:
    """Tests for ReductoClient."""

    def setup_method(self) -> None:
        self.client = ReductoClient(api_key="test-key", base_url="https://test.reducto.ai")

    def test_client_init(self) -> None:
        client = ReductoClient(api_key="key123")
        assert client._api_key == "key123"
        assert client._base_url == "https://platform.reducto.ai"

    def test_client_strips_trailing_slash(self) -> None:
        client = ReductoClient(api_key="k", base_url="https://example.com/")
        assert client._base_url == "https://example.com"

    @pytest.mark.asyncio
    async def test_parse_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            await self.client.parse("/nonexistent/file.pdf")

    @pytest.mark.asyncio
    async def test_parse_success(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"fake pdf content")

        upload_resp = MagicMock()
        upload_resp.raise_for_status = MagicMock()
        upload_resp.json.return_value = {"file_id": "reducto://file-123.pdf"}

        parse_resp = MagicMock()
        parse_resp.raise_for_status = MagicMock()
        parse_resp.json.return_value = {
            "job_id": "job-1",
            "usage": {"num_pages": 2, "credits": 3.0},
            "result": {
                "chunks": [
                    {"content": "# Title"},
                    {"content": "Body text"},
                ],
            },
        }

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=[upload_resp, parse_resp])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await self.client.parse(str(test_file))

        assert result == "# Title\n\nBody text"

    @pytest.mark.asyncio
    async def test_parse_sends_correct_payload(self, tmp_path: Path) -> None:
        """Verify the parse request uses 'input' field and markdown formatting."""
        test_file = tmp_path / "doc.pdf"
        test_file.write_bytes(b"pdf bytes")

        upload_resp = MagicMock()
        upload_resp.raise_for_status = MagicMock()
        upload_resp.json.return_value = {"file_id": "reducto://abc.pdf"}

        parse_resp = MagicMock()
        parse_resp.raise_for_status = MagicMock()
        parse_resp.json.return_value = {
            "job_id": "j1",
            "usage": {},
            "result": {"chunks": [{"content": "ok"}]},
        }

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=[upload_resp, parse_resp])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            await self.client.parse(str(test_file))

            # Second call is the parse request
            parse_call = mock_client.post.call_args_list[1]
            payload = parse_call.kwargs.get("json", {})
            assert payload["input"] == "reducto://abc.pdf"
            assert payload["formatting"] == {"table_output_format": "md"}

    @pytest.mark.asyncio
    async def test_parse_sends_auth_header(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"fake pdf content")

        upload_resp = MagicMock()
        upload_resp.raise_for_status = MagicMock()
        upload_resp.json.return_value = {"file_id": "reducto://file-123.pdf"}

        parse_resp = MagicMock()
        parse_resp.raise_for_status = MagicMock()
        parse_resp.json.return_value = {
            "job_id": "j1",
            "usage": {},
            "result": {"chunks": [{"content": "parsed"}]},
        }

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=[upload_resp, parse_resp])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            await self.client.parse(str(test_file))

            # Both calls should have auth header
            for call in mock_client.post.call_args_list:
                headers = call.kwargs.get("headers", {})
                assert headers["Authorization"] == "Bearer test-key"

    @pytest.mark.asyncio
    async def test_classify_uploads_and_sends_schema(self, tmp_path: Path) -> None:
        test_file = tmp_path / "lpa.pdf"
        test_file.write_bytes(b"pdf")
        upload_resp = MagicMock()
        upload_resp.raise_for_status = MagicMock()
        upload_resp.json.return_value = {"file_id": "reducto://lpa.pdf"}
        classify_resp = MagicMock()
        classify_resp.raise_for_status = MagicMock()
        classify_resp.json.return_value = {
            "job_id": "classify-1",
            "result": {"category": "Limited Partnership Agreement"},
            "response_confidence": {
                "categories": [
                    {
                        "category": "Limited Partnership Agreement",
                        "confidence": 0.75,
                        "criteria_confidence": [
                            {"criterion": "contains fund terms", "confidence": "high"}
                        ],
                    }
                ]
            },
        }

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=[upload_resp, classify_resp])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await self.client.classify(
                test_file,
                categories=[
                    {
                        "id": "cat-1",
                        "name": "Limited Partnership Agreement",
                        "classification_criteria": "contains fund terms",
                    }
                ],
            )

        payload = mock_client.post.call_args_list[1].kwargs["json"]
        assert payload["input"] == "reducto://lpa.pdf"
        assert payload["classification_schema"] == [
            {
                "category": "Limited Partnership Agreement",
                "criteria": ["contains fund terms"],
            }
        ]
        assert result.category_name == "Limited Partnership Agreement"
        assert result.confidence == 75

    @pytest.mark.asyncio
    async def test_extract_uses_citations_and_schema(self, tmp_path: Path) -> None:
        test_file = tmp_path / "sub.pdf"
        test_file.write_bytes(b"pdf")
        upload_resp = MagicMock()
        upload_resp.raise_for_status = MagicMock()
        upload_resp.json.return_value = {"file_id": "reducto://sub.pdf"}
        extract_resp = MagicMock()
        extract_resp.raise_for_status = MagicMock()
        extract_resp.json.return_value = {
            "job_id": "extract-1",
            "result": {
                "fund_name": {
                    "value": "Horizon IV",
                    "citations": [{"content": "Fund name: Horizon IV", "confidence": "high"}],
                }
            },
        }

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=[upload_resp, extract_resp])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await self.client.extract(
                test_file,
                extraction_fields=[
                    {
                        "field_name": "fund_name",
                        "description": "Fund legal name",
                        "data_type": "string",
                    }
                ],
            )

        payload = mock_client.post.call_args_list[1].kwargs["json"]
        assert payload["input"] == "reducto://sub.pdf"
        assert payload["settings"]["citations"]["enabled"] is True
        assert payload["instructions"]["schema"]["properties"]["fund_name"]["type"] == "string"
        assert result.fields[0].field_name == "fund_name"
        assert result.fields[0].extracted_value == "Horizon IV"
        assert result.fields[0].confidence == "high"

    @pytest.mark.asyncio
    async def test_parse_with_retrieval_chunks_sends_chunking_payload(self, tmp_path: Path) -> None:
        test_file = tmp_path / "doc.pdf"
        test_file.write_bytes(b"pdf")
        upload_resp = MagicMock()
        upload_resp.raise_for_status = MagicMock()
        upload_resp.json.return_value = {"file_id": "reducto://doc.pdf"}
        parse_resp = MagicMock()
        parse_resp.raise_for_status = MagicMock()
        parse_resp.json.return_value = {
            "job_id": "parse-1",
            "usage": {},
            "result": {
                "chunks": [
                    {
                        "content": "chunk one",
                        "blocks": [{"bbox": {"page": 1}, "type": "Text"}],
                    }
                ]
            },
        }

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=[upload_resp, parse_resp])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await self.client.parse_with_retrieval_chunks(test_file, chunk_size=800)

        payload = mock_client.post.call_args_list[1].kwargs["json"]
        assert payload["retrieval"]["chunking"] == {
            "chunk_mode": "variable",
            "chunk_size": 800,
        }
        assert result.chunks[0].text == "chunk one"
        assert result.chunks[0].metadata["provider"] == "reducto"

    @pytest.mark.asyncio
    async def test_parse_retries_on_parse_failure(self, tmp_path: Path) -> None:
        """Parse retries should not re-upload the file."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"fake pdf content")

        upload_resp = MagicMock()
        upload_resp.raise_for_status = MagicMock()
        upload_resp.json.return_value = {"file_id": "reducto://file-123.pdf"}

        fail_resp = MagicMock()
        fail_resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())
        )

        success_resp = MagicMock()
        success_resp.raise_for_status = MagicMock()
        success_resp.json.return_value = {
            "job_id": "j2",
            "usage": {},
            "result": {"chunks": [{"content": "recovered"}]},
        }

        with (
            patch("httpx.AsyncClient") as mock_cls,
            patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            mock_client = AsyncMock()
            # upload succeeds, first parse fails, second parse succeeds
            mock_client.post = AsyncMock(side_effect=[upload_resp, fail_resp, success_resp])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await self.client.parse(str(test_file))

        assert result == "recovered"
        assert mock_client.post.call_count == 3  # 1 upload + 2 parse attempts
        mock_sleep.assert_awaited_once()  # backoff between parse retries

    @pytest.mark.asyncio
    async def test_upload_retries_on_failure(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"fake pdf content")

        with (
            patch("httpx.AsyncClient") as mock_cls,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(
                side_effect=httpx.RequestError("Connection failed")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            with pytest.raises(ReductoParseError, match="upload failed"):
                await self.client.parse(str(test_file))

            assert mock_client.post.call_count == 3  # 3 upload retries

    @pytest.mark.asyncio
    async def test_all_parse_retries_exhausted(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"fake pdf content")

        upload_resp = MagicMock()
        upload_resp.raise_for_status = MagicMock()
        upload_resp.json.return_value = {"file_id": "reducto://file-123.pdf"}

        with (
            patch("httpx.AsyncClient") as mock_cls,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_client = AsyncMock()
            fail = httpx.RequestError("timeout")
            mock_client.post = AsyncMock(side_effect=[upload_resp, fail, fail, fail])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            with pytest.raises(ReductoParseError, match="parsing failed"):
                await self.client.parse(str(test_file))

    @pytest.mark.asyncio
    async def test_upload_no_file_id_raises(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"content")

        upload_resp = MagicMock()
        upload_resp.raise_for_status = MagicMock()
        upload_resp.json.return_value = {}  # no file_id

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=upload_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            with pytest.raises(ReductoParseError, match="no file_id"):
                await self.client.parse(str(test_file))

    @pytest.mark.asyncio
    async def test_parse_empty_chunks_raises(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"content")

        upload_resp = MagicMock()
        upload_resp.raise_for_status = MagicMock()
        upload_resp.json.return_value = {"file_id": "reducto://f.pdf"}

        parse_resp = MagicMock()
        parse_resp.raise_for_status = MagicMock()
        parse_resp.json.return_value = {
            "job_id": "j3",
            "usage": {},
            "result": {"chunks": []},
        }

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=[upload_resp, parse_resp])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            with pytest.raises(ReductoParseError, match="no chunks"):
                await self.client.parse(str(test_file))
