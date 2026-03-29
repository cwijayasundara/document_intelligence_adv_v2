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
