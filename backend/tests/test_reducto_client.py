"""Tests for the Reducto client."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.parser.reducto import ReductoClient, ReductoParseError


class TestReductoClient:
    """Tests for ReductoClient."""

    def setup_method(self) -> None:
        self.client = ReductoClient(
            api_key="test-key", api_url="https://test.reducto.ai/parse"
        )

    @pytest.mark.asyncio
    async def test_parse_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            await self.client.parse("/nonexistent/file.pdf")

    @pytest.mark.asyncio
    async def test_parse_success(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"fake pdf content")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "result": {"content": "# Parsed markdown"}
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await self.client.parse(str(test_file))
            assert result == "# Parsed markdown"

    @pytest.mark.asyncio
    async def test_parse_retries_on_failure(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"fake pdf content")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(
                side_effect=httpx.RequestError("Connection failed")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(ReductoParseError):
                await self.client.parse(str(test_file))

    @pytest.mark.asyncio
    async def test_parse_sends_auth_header(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"fake pdf content")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"result": {"content": "parsed"}}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await self.client.parse(str(test_file))

            call_kwargs = mock_client.post.call_args
            headers = call_kwargs.kwargs.get("headers", {})
            assert headers.get("Authorization") == "Bearer test-key"

    def test_client_init(self) -> None:
        client = ReductoClient(api_key="key123")
        assert client._api_key == "key123"
