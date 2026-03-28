"""Local filesystem storage operations for document files."""

import hashlib
from pathlib import Path

import aiofiles


class LocalStorage:
    """Handle local filesystem operations for document storage."""

    def __init__(self, upload_dir: str, parsed_dir: str) -> None:
        self._upload_dir = Path(upload_dir)
        self._parsed_dir = Path(parsed_dir)
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        self._parsed_dir.mkdir(parents=True, exist_ok=True)

    @property
    def upload_dir(self) -> Path:
        """Return the upload directory path."""
        return self._upload_dir

    @property
    def parsed_dir(self) -> Path:
        """Return the parsed directory path."""
        return self._parsed_dir

    async def save_file(self, filename: str, content: bytes) -> Path:
        """Save file content to the upload directory.

        Returns:
            The full path where the file was saved.
        """
        dest = self._upload_dir / filename
        async with aiofiles.open(dest, "wb") as f:
            await f.write(content)
        return dest

    async def delete_file(self, file_path: str | Path) -> bool:
        """Delete a file. Returns True if it existed and was deleted."""
        p = Path(file_path)
        if p.exists():
            p.unlink()
            return True
        return False

    def file_exists(self, file_path: str | Path) -> bool:
        """Check if a file exists."""
        return Path(file_path).exists()

    @staticmethod
    def compute_sha256(content: bytes) -> str:
        """Compute SHA-256 hex digest for file content."""
        return hashlib.sha256(content).hexdigest()
