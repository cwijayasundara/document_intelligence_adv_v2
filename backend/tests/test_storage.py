"""Tests for LocalStorage operations."""

import hashlib
from pathlib import Path

import pytest

from src.storage.local import LocalStorage


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorage:
    upload = tmp_path / "upload"
    parsed = tmp_path / "parsed"
    return LocalStorage(str(upload), str(parsed))


async def test_save_file(storage: LocalStorage) -> None:
    """save_file writes content and returns the path."""
    content = b"Hello, World!"
    path = await storage.save_file("test.txt", content)
    assert path.exists()
    assert path.read_bytes() == content


async def test_delete_file(storage: LocalStorage) -> None:
    """delete_file removes an existing file."""
    path = await storage.save_file("del.txt", b"data")
    assert path.exists()
    result = await storage.delete_file(path)
    assert result is True
    assert not path.exists()


async def test_delete_nonexistent(storage: LocalStorage) -> None:
    """delete_file returns False for nonexistent file."""
    result = await storage.delete_file("/nonexistent/file.txt")
    assert result is False


def test_file_exists(storage: LocalStorage, tmp_path: Path) -> None:
    """file_exists returns True/False correctly."""
    test_file = tmp_path / "exists.txt"
    test_file.write_text("hi")
    assert storage.file_exists(test_file) is True
    assert storage.file_exists(tmp_path / "nope.txt") is False


def test_compute_sha256() -> None:
    """compute_sha256 returns correct hex digest."""
    content = b"test content"
    expected = hashlib.sha256(content).hexdigest()
    assert LocalStorage.compute_sha256(content) == expected


def test_directories_created(tmp_path: Path) -> None:
    """LocalStorage creates directories on init."""
    upload = tmp_path / "new_upload"
    parsed = tmp_path / "new_parsed"
    LocalStorage(str(upload), str(parsed))
    assert upload.exists()
    assert parsed.exists()


def test_upload_dir_property(storage: LocalStorage) -> None:
    """upload_dir property returns correct path."""
    assert isinstance(storage.upload_dir, Path)


def test_parsed_dir_property(storage: LocalStorage) -> None:
    """parsed_dir property returns correct path."""
    assert isinstance(storage.parsed_dir, Path)


@pytest.mark.parametrize(
    "malicious_name",
    [
        "../etc/passwd",
        "../../secret.txt",
        "foo/../../bar.txt",
        "/etc/passwd",
        "..\\windows\\system32\\config",
        "..",
        ".",
    ],
)
async def test_path_traversal_rejected(storage: LocalStorage, malicious_name: str) -> None:
    """save_file rejects filenames that attempt path traversal."""
    with pytest.raises(ValueError, match="Invalid filename"):
        await storage.save_file(malicious_name, b"malicious content")
