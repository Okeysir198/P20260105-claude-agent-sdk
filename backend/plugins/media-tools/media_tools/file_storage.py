"""Lightweight file storage for media tools plugin.

Uses DATA_DIR environment variable for base path. No imports from the backend.
"""
import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=4)


def _get_data_dir() -> Path:
    """Get data directory from DATA_DIR environment variable."""
    data_dir = os.environ.get("DATA_DIR")
    if not data_dir:
        raise ValueError("DATA_DIR environment variable is required for media tools")
    return Path(data_dir)


@dataclass
class FileMetadata:
    safe_name: str
    original_name: str
    file_type: Literal["input", "output"]
    size_bytes: int
    content_type: str
    created_at: str
    session_id: str

    def to_dict(self) -> dict:
        return asdict(self)


# Allowed file extensions (lowercase, without dot)
ALLOWED_EXTENSIONS = {
    "pdf", "doc", "docx", "xls", "xlsx", "txt", "md", "csv", "json",
    "png", "jpg", "jpeg", "gif", "webp", "svg",
    "webm", "mp3", "wav", "ogg", "m4a", "aac", "flac", "opus",
    "mp4", "mov", "avi", "mkv",
    "py", "js", "ts", "jsx", "tsx", "html", "css",
    "zip", "tar", "gz",
}

MIME_TYPES = {
    "pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg",
    "jpeg": "image/jpeg", "gif": "image/gif", "webp": "image/webp",
    "svg": "image/svg+xml", "webm": "audio/webm", "mp3": "audio/mpeg",
    "wav": "audio/wav", "ogg": "audio/ogg", "m4a": "audio/mp4",
    "aac": "audio/aac", "flac": "audio/flac", "opus": "audio/opus",
    "mp4": "video/mp4", "mov": "video/quicktime",
    "txt": "text/plain", "md": "text/markdown", "csv": "text/csv",
    "json": "application/json",
}


def _write_file_atomic(path: Path, content: bytes) -> None:
    with open(path, "wb") as f:
        f.write(content)


class FileStorage:
    """Per-session file storage using DATA_DIR env var."""

    def __init__(self, username: str, session_id: str):
        if not username:
            raise ValueError("Username is required for file storage")
        if not session_id:
            raise ValueError("Session ID is required for file storage")

        self._username = username
        self._session_id = session_id
        base_path = _get_data_dir()
        self._session_dir = base_path / username / "files" / session_id
        self._input_dir = self._session_dir / "input"
        self._output_dir = self._session_dir / "output"

    def get_session_dir(self) -> Path:
        return self._session_dir

    def get_input_dir(self) -> Path:
        self._input_dir.mkdir(parents=True, exist_ok=True)
        return self._input_dir

    def get_output_dir(self) -> Path:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        return self._output_dir

    def _ensure_directories(self) -> None:
        self._input_dir.mkdir(parents=True, exist_ok=True)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def sanitize_filename(self, filename: str) -> str:
        name = Path(filename).name
        stem = name
        ext = ""
        if "." in name:
            parts = name.rsplit(".", 1)
            stem, ext = parts[0], parts[1]
        safe_stem = "".join(c for c in stem if c.isalnum() or c in "-_.")
        if not safe_stem:
            safe_stem = "file"
        if ext and ext.lower() in ALLOWED_EXTENSIONS:
            return f"{safe_stem}.{ext}"
        return safe_stem

    def _guess_content_type(self, filename: str) -> str:
        ext = Path(filename).suffix.lstrip(".").lower()
        return MIME_TYPES.get(ext, "application/octet-stream")

    async def save_input_file(
        self, content: bytes, filename: str, content_type: str = ""
    ) -> FileMetadata:
        """Save a user-uploaded file to the input directory."""
        self._ensure_directories()
        safe_name = self.sanitize_filename(filename)
        target_path = self._input_dir / safe_name

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(_executor, _write_file_atomic, target_path, content)

        return FileMetadata(
            safe_name=safe_name,
            original_name=filename,
            file_type="input",
            size_bytes=len(content),
            content_type=content_type or self._guess_content_type(filename),
            created_at=datetime.now().isoformat(),
            session_id=self._session_id,
        )

    async def delete_file(self, filename: str, file_type: str = "input") -> None:
        """Delete a file from the specified directory."""
        target_dir = self._input_dir if file_type == "input" else self._output_dir
        path = target_dir / self.sanitize_filename(filename)
        if path.exists():
            path.unlink()

    async def save_output_file(self, filename: str, content: bytes) -> FileMetadata:
        self._ensure_directories()
        safe_name = self.sanitize_filename(filename)
        target_path = self._output_dir / safe_name
        temp_path = target_path.with_suffix(".tmp")

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(_executor, _write_file_atomic, temp_path, content)
        temp_path.replace(target_path)

        return FileMetadata(
            safe_name=safe_name,
            original_name=filename,
            file_type="output",
            size_bytes=len(content),
            content_type=self._guess_content_type(filename),
            created_at=datetime.now().isoformat(),
            session_id=self._session_id,
        )
