"""Per-session file storage: data/{username}/files/{session_id}/input|output."""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Literal

from agent import PROJECT_ROOT

logger = logging.getLogger(__name__)

# Thread pool for file I/O operations
_executor = ThreadPoolExecutor(max_workers=4)

def _write_file_atomic(path: Path, content: bytes) -> None:
    """Write content to file. Blocking -- meant for executor use."""
    with open(path, "wb") as f:
        f.write(content)

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
MAX_SESSION_SIZE_BYTES = 500 * 1024 * 1024
MAX_FILES_PER_SESSION = 100

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


class FileStorageError(Exception):
    """Base exception for file storage errors."""
    pass


class FileSizeExceededError(FileStorageError):
    """Raised when file size exceeds limits."""
    pass


class SessionSizeExceededError(FileStorageError):
    """Raised when session total size exceeds limits."""
    pass


class FileCountExceededError(FileStorageError):
    """Raised when file count exceeds limits."""
    pass


class InvalidFileTypeError(FileStorageError):
    """Raised when file type is not allowed."""
    pass


class FileNotFound(FileStorageError):
    """Raised when requested file doesn't exist."""
    pass


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


class FileStorage:
    """Per-session file storage with input/output subdirectories."""

    def __init__(self, username: str, session_id: str, base_path: str = "data"):
        if not username:
            raise ValueError("Username is required for file storage")
        if not session_id:
            raise ValueError("Session ID is required for file storage")

        self._username = username
        self._session_id = session_id
        self._base_path = Path(base_path) if isinstance(base_path, str) else base_path
        if not self._base_path.is_absolute():
            self._base_path = PROJECT_ROOT / self._base_path

        self._session_dir = self._base_path / username / "files" / session_id
        self._input_dir = self._session_dir / "input"
        self._output_dir = self._session_dir / "output"

    def get_session_dir(self) -> Path:
        """Get the session root directory (parent of input/ and output/)."""
        return self._session_dir

    def get_input_dir(self) -> Path:
        """Get the input directory path for SDK access."""
        return self._input_dir

    def get_output_dir(self) -> Path:
        """Get the output directory path for SDK access."""
        return self._output_dir

    def _ensure_directories(self) -> None:
        """Create storage directories if they don't exist."""
        self._input_dir.mkdir(parents=True, exist_ok=True)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"File storage directories ready: {self._session_dir}")

    def _get_dir(self, file_type: Literal["input", "output"]) -> Path:
        """Get directory path for a file type."""
        if file_type == "input":
            return self._input_dir
        if file_type == "output":
            return self._output_dir
        raise ValueError(f"Invalid file_type: {file_type}. Must be 'input' or 'output'")

    async def _get_session_totals(self) -> tuple[int, int]:
        """Get (total_files, total_size_bytes) for the session."""
        loop = asyncio.get_running_loop()

        def _calculate_totals():
            total_files = 0
            total_size = 0
            for dir_path in (self._input_dir, self._output_dir):
                if dir_path.exists():
                    for file_path in dir_path.iterdir():
                        if file_path.is_file():
                            total_files += 1
                            total_size += file_path.stat().st_size
            return total_files, total_size

        return await loop.run_in_executor(_executor, _calculate_totals)

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal. Preserves allowed extensions."""
        name = Path(filename).name
        stem = name
        ext = ""

        if "." in name:
            parts = name.rsplit(".", 1)
            stem, ext = parts[0], parts[1]

        # Remove path separators and special characters
        safe_stem = "".join(c for c in stem if c.isalnum() or c in "-_.")

        # Ensure we have something
        if not safe_stem:
            safe_stem = "file"

        # Add extension back if it was allowed
        if ext and ext.lower() in ALLOWED_EXTENSIONS:
            safe_name = f"{safe_stem}.{ext}"
        else:
            safe_name = safe_stem

        # Add timestamp for uniqueness if needed
        return safe_name

    async def validate_file(self, filename: str, size: int) -> None:
        """Validate file against size and count constraints."""
        if size > MAX_FILE_SIZE_BYTES:
            raise FileSizeExceededError(
                f"File size ({size} bytes) exceeds maximum allowed "
                f"({MAX_FILE_SIZE_BYTES} bytes = {MAX_FILE_SIZE_BYTES // (1024*1024)}MB)"
            )

        current_files, current_size = await self._get_session_totals()

        if current_files >= MAX_FILES_PER_SESSION:
            raise FileCountExceededError(
                f"Session has reached maximum file count ({MAX_FILES_PER_SESSION})"
            )

        if current_size + size > MAX_SESSION_SIZE_BYTES:
            raise SessionSizeExceededError(
                f"Session size would exceed maximum allowed "
                f"({MAX_SESSION_SIZE_BYTES} bytes = {MAX_SESSION_SIZE_BYTES // (1024*1024)}MB). "
                f"Current: {current_size} bytes, new file: {size} bytes"
            )

    def _guess_content_type(self, filename: str) -> str:
        """Guess MIME type from filename extension."""
        ext = Path(filename).suffix.lstrip(".").lower()
        return MIME_TYPES.get(ext, "application/octet-stream")

    async def _make_safe_name_unique(self, safe_name: str, file_type: Literal["input", "output"]) -> str:
        """Append counter suffix if filename already exists in target directory."""
        target_dir = self._get_dir(file_type)
        counter = 0
        unique_name = safe_name
        loop = asyncio.get_running_loop()

        def check_exists():
            return (target_dir / unique_name).exists()

        while await loop.run_in_executor(_executor, check_exists):
            stem = Path(safe_name).stem
            ext = Path(safe_name).suffix
            counter += 1
            unique_name = f"{stem}_{counter}{ext}"

        return unique_name

    async def _save_file(
        self,
        content: bytes,
        filename: str,
        file_type: Literal["input", "output"],
        content_type: str = "",
        validate: bool = True,
    ) -> FileMetadata:
        """Save file content to the specified directory with atomic write."""
        self._ensure_directories()

        size = len(content)
        original_name = filename

        # Validate if requested
        if validate:
            await self.validate_file(original_name, size)

        safe_name = self.sanitize_filename(original_name)
        safe_name = await self._make_safe_name_unique(safe_name, file_type)

        target_dir = self._get_dir(file_type)
        target_path = target_dir / safe_name
        temp_path = target_path.with_suffix(".tmp")

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(_executor, _write_file_atomic, temp_path, content)
            temp_path.replace(target_path)

            metadata = FileMetadata(
                safe_name=safe_name,
                original_name=original_name,
                file_type=file_type,
                size_bytes=size,
                content_type=content_type or self._guess_content_type(original_name),
                created_at=datetime.now().isoformat(),
                session_id=self._session_id,
            )

            logger.info(
                f"Saved {file_type} file: {original_name} -> {safe_name} "
                f"({size} bytes) for session {self._session_id}"
            )
            return metadata

        except IOError as e:
            if temp_path.exists():
                temp_path.unlink()
            raise FileStorageError(f"Failed to save file: {e}") from e

    async def save_input_file(
        self, content: bytes, filename: str, content_type: str = "", validate: bool = True
    ) -> FileMetadata:
        """Save a user-uploaded file to the input directory."""
        if not filename:
            raise FileStorageError("Upload file has no filename")

        return await self._save_file(content, filename, "input", content_type, validate)

    async def save_output_file(
        self, filename: str, content: bytes, validate: bool = True
    ) -> FileMetadata:
        """Save an SDK-generated file to the output directory."""
        return await self._save_file(content, filename, "output", "", validate)

    async def list_files(
        self, file_type: Literal["input", "output"] | None = None
    ) -> list[FileMetadata]:
        """List files in session storage, newest first. None returns both types."""
        loop = asyncio.get_running_loop()

        def _list_files_sync():
            results = []
            file_types: list[Literal["input", "output"]] = [file_type] if file_type else ["input", "output"]

            for ft in file_types:
                dir_path = self._get_dir(ft)
                if not dir_path.exists():
                    continue

                for file_path in dir_path.iterdir():
                    if file_path.is_file():
                        stat = file_path.stat()
                        metadata = FileMetadata(
                            safe_name=file_path.name,
                            original_name=file_path.name,
                            file_type=ft,
                            size_bytes=stat.st_size,
                            content_type=self._guess_content_type(file_path.name),
                            created_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            session_id=self._session_id,
                        )
                        results.append(metadata)

            results.sort(key=lambda m: m.created_at, reverse=True)
            return results

        return await loop.run_in_executor(_executor, _list_files_sync)

    async def delete_file(self, safe_name: str, file_type: Literal["input", "output"]) -> bool:
        """Delete a file. Returns True if deleted, False if not found."""
        dir_path = self._get_dir(file_type)
        file_path = dir_path / safe_name

        loop = asyncio.get_running_loop()

        def _delete_sync():
            if file_path.exists() and file_path.is_file():
                try:
                    file_path.unlink()
                    logger.info(
                        f"Deleted {file_type} file: {safe_name} "
                        f"from session {self._session_id}"
                    )
                    return True
                except IOError as e:
                    logger.error(f"Failed to delete file {safe_name}: {e}")
                    return False
            return False

        return await loop.run_in_executor(_executor, _delete_sync)

    def get_file_path(self, safe_name: str, file_type: Literal["input", "output"]) -> Path:
        """Get filesystem path for a file. Raises FileNotFound if missing."""
        dir_path = self._get_dir(file_type)
        file_path = dir_path / safe_name

        if not file_path.exists():
            raise FileNotFound(
                f"File not found: {safe_name} in {file_type} directory "
                f"for session {self._session_id}"
            )

        return file_path


def get_user_file_storage(username: str, session_id: str) -> FileStorage:
    """Get FileStorage instance for a user session."""
    if not username:
        raise ValueError("Username is required for file storage access")
    if not session_id:
        raise ValueError("Session ID is required for file storage access")

    return FileStorage(username=username, session_id=session_id)


def delete_session_files(username: str, session_id: str, base_path: str = "data") -> bool:
    """Delete entire file storage directory for a session. Returns True if deleted."""
    import shutil

    if not username or not session_id:
        return False

    bp = Path(base_path)
    if not bp.is_absolute():
        bp = PROJECT_ROOT / bp

    session_dir = bp / username / "files" / session_id
    if session_dir.exists() and session_dir.is_dir():
        shutil.rmtree(session_dir)
        logger.info(f"Deleted session file directory: {session_dir}")
        return True

    return False
