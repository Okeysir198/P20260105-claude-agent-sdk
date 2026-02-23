"""Shared storage utilities for directory management, file sanitization, and data paths."""
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Literal

from agent import PROJECT_ROOT

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)


def get_data_dir() -> Path:
    """Get data directory from DATA_DIR env var or PROJECT_ROOT/data."""
    data_dir_env = os.environ.get("DATA_DIR")
    if data_dir_env:
        return Path(data_dir_env)
    return PROJECT_ROOT / "data"


def get_user_data_dir(username: str) -> Path:
    """Get user data directory: data/{username}/. Raises ValueError if username is empty."""
    if not username:
        raise ValueError("Username is required for storage access")
    return get_data_dir() / username


def ensure_directory(path: Path, name: str = "directory") -> Path:
    """Create a directory if it doesn't exist and return it."""
    path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"{name.capitalize()} ready: {path}")
    return path


def sanitize_filesystem_name(name: str, allowed_extra: str = "-_") -> str:
    """Keep only alphanumeric chars and allowed_extra characters."""
    return "".join(c for c in name if c.isalnum() or c in allowed_extra)


ALLOWED_EXTENSIONS = {
    "pdf", "doc", "docx", "xls", "xlsx", "txt", "md", "csv", "json",
    "png", "jpg", "jpeg", "gif", "webp", "svg",
    "webm", "mp3", "wav", "ogg", "m4a", "aac", "flac", "opus",
    "mp4", "webm", "mov", "avi", "mkv",
    "py", "js", "ts", "jsx", "tsx", "html", "css",
    "zip", "tar", "gz",
}

MIME_TYPES = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "txt": "text/plain",
    "md": "text/markdown",
    "csv": "text/csv",
    "json": "application/json",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "svg": "image/svg+xml",
    "webm": "audio/webm",
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
    "m4a": "audio/mp4",
    "aac": "audio/aac",
    "flac": "audio/flac",
    "opus": "audio/opus",
    "mp4": "video/mp4",
    "mov": "video/quicktime",
    "avi": "video/x-msvideo",
    "mkv": "video/x-matroska",
    "py": "text/x-python",
    "js": "text/javascript",
    "ts": "text/typescript",
    "jsx": "text/jsx",
    "tsx": "text/tsx",
    "html": "text/html",
    "css": "text/css",
    "zip": "application/zip",
    "tar": "application/x-tar",
    "gz": "application/gzip",
}


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal. Preserves allowed extensions."""
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
        safe_name = f"{safe_stem}.{ext}"
    else:
        safe_name = safe_stem

    return safe_name


def guess_content_type(filename: str) -> str:
    """Guess MIME type from filename extension."""
    ext = Path(filename).suffix.lstrip(".").lower()
    return MIME_TYPES.get(ext, "application/octet-stream")


def write_file_atomic(path: Path, content: bytes) -> None:
    """Write content to file. Blocking -- meant for executor use."""
    with open(path, "wb") as f:
        f.write(content)


@dataclass
class FileMetadata:
    """Metadata for a stored file."""
    safe_name: str
    original_name: str
    file_type: Literal["input", "output"]
    size_bytes: int
    content_type: str
    created_at: str
    session_id: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


def validate_username(username: str) -> None:
    """Raise ValueError if username is empty or None."""
    if not username:
        raise ValueError("Username is required for storage access")


def resolve_base_path(base_path: str | Path) -> Path:
    """Resolve base path to absolute Path, relative to PROJECT_ROOT if needed."""
    path = Path(base_path) if isinstance(base_path, str) else base_path
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path
