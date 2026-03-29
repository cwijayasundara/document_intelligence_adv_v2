"""Local filesystem storage operations for document files."""

import hashlib
import logging
from pathlib import Path

import aiofiles

logger = logging.getLogger(__name__)


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

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitize a filename to prevent path traversal attacks.

        Rejects names containing '..' or path separators, then extracts
        just the basename component.

        Raises:
            ValueError: If the filename is invalid or attempts path traversal.
        """
        if not filename or ".." in filename or "/" in filename or "\\" in filename:
            raise ValueError(f"Invalid filename: {filename!r}")

        # Extract just the filename component (no directory parts)
        safe_name = Path(filename).name

        if not safe_name or safe_name in {".", ".."}:
            raise ValueError(f"Invalid filename: {filename!r}")

        return safe_name

    async def save_file(self, filename: str, content: bytes) -> Path:
        """Save file content to the upload directory.

        Returns:
            The full path where the file was saved.

        Raises:
            ValueError: If the filename is invalid or attempts path traversal.
        """
        safe_name = self._sanitize_filename(filename)
        dest = (self._upload_dir / safe_name).resolve()

        # Ensure the resolved path is still within the upload directory
        upload_resolved = self._upload_dir.resolve()
        if not str(dest).startswith(str(upload_resolved) + "/") and dest != upload_resolved:
            raise ValueError(f"Invalid filename: {filename!r}")

        async with aiofiles.open(dest, "wb") as f:
            await f.write(content)
        logger.info("Saved file %s (%d bytes)", safe_name, len(content))
        return dest

    async def delete_file(self, file_path: str | Path) -> bool:
        """Delete a file. Returns True if it existed and was deleted."""
        p = Path(file_path)
        if p.exists():
            p.unlink()
            logger.info("Deleted file %s", p.name)
            return True
        logger.debug("Delete skipped, file not found: %s", file_path)
        return False

    def file_exists(self, file_path: str | Path) -> bool:
        """Check if a file exists."""
        return Path(file_path).exists()

    @staticmethod
    def compute_sha256(content: bytes) -> str:
        """Compute SHA-256 hex digest for file content."""
        return hashlib.sha256(content).hexdigest()
