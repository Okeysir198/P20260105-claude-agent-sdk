"""File storage service for session file management.

Provides per-session file storage for user uploads and SDK-generated files.
Files are organized under data/{username}/files/{session_id}/input|output.

Usage:
    from agent.core.file_storage import FileStorage

    storage = FileStorage(username="john", session_id="sess-123")
    metadata = await storage.save_input_file(upload_file)
    files = await storage.list_files(file_type="input")
"""
import asyncio
import hashlib
import logging
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from fastapi import UploadFile

from agent import PROJECT_ROOT

logger = logging.getLogger(__name__)

# Thread pool for file I/O operations
_executor = ThreadPoolExecutor(max_workers=4)

def _write_file_atomic(path: Path, content: bytes) -> None:
    """Write content to file atomically.

    Args:
        path: Target file path
        content: Bytes to write

    This is a blocking function meant to be run in an executor.
    """
    with open(path, "wb") as f:
        f.write(content)

# File storage limits
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB per file
MAX_SESSION_SIZE_BYTES = 500 * 1024 * 1024  # 500MB per session
MAX_FILES_PER_SESSION = 100

# Allowed file extensions (lowercase, without dot)
ALLOWED_EXTENSIONS = {
    # Documents
    "pdf", "doc", "docx", "xls", "xlsx", "txt", "md", "csv", "json",
    # Images
    "png", "jpg", "jpeg", "gif", "webp", "svg",
    # Code
    "py", "js", "ts", "jsx", "tsx", "html", "css",
    # Archives
    "zip", "tar", "gz",
}

# MIME type mapping for common extensions
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


class FileMetadata:
    """Metadata for a stored file.

    Attributes:
        safe_name: Sanitized filename (used for storage)
        original_name: Original filename from upload
        file_type: Type of file ("input" or "output")
        size_bytes: File size in bytes
        content_type: MIME type of the file
        created_at: ISO timestamp of file creation
        session_id: Session ID this file belongs to
    """

    def __init__(
        self,
        safe_name: str,
        original_name: str,
        file_type: Literal["input", "output"],
        size_bytes: int,
        content_type: str,
        created_at: str,
        session_id: str,
    ):
        self.safe_name = safe_name
        self.original_name = original_name
        self.file_type = file_type
        self.size_bytes = size_bytes
        self.content_type = content_type
        self.created_at = created_at
        self.session_id = session_id

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "safe_name": self.safe_name,
            "original_name": self.original_name,
            "file_type": self.file_type,
            "size_bytes": self.size_bytes,
            "content_type": self.content_type,
            "created_at": self.created_at,
            "session_id": self.session_id,
        }


class FileStorage:
    """Per-session file storage manager.

    Provides methods to save, list, delete, and retrieve files for a specific
    user session. Files are stored under data/{username}/files/{session_id}/
    with separate subdirectories for input (user uploads) and output (SDK-generated)
    files.

    Args:
        username: Username for data isolation
        session_id: Session ID for file grouping
        base_path: Base directory for file storage (default: "data")

    Raises:
        ValueError: If username or session_id is empty
    """

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

        # Directory structure: data/{username}/files/{session_id}/
        self._session_dir = self._base_path / username / "files" / session_id
        self._input_dir = self._session_dir / "input"
        self._output_dir = self._session_dir / "output"

        # Create directories on first access
        self._ensure_directories()

    def get_session_dir(self) -> Path:
        """Get the session root directory (parent of input/ and output/)."""
        self._ensure_directories()
        return self._session_dir

    def get_input_dir(self) -> Path:
        """Get the input directory path for SDK access."""
        self._ensure_directories()
        return self._input_dir

    def get_output_dir(self) -> Path:
        """Get the output directory path for SDK access."""
        self._ensure_directories()
        return self._output_dir

    def _ensure_directories(self) -> None:
        """Create storage directories if they don't exist."""
        self._input_dir.mkdir(parents=True, exist_ok=True)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"File storage directories ready: {self._session_dir}")

    def _get_dir(self, file_type: Literal["input", "output"]) -> Path:
        """Get the directory path for a file type.

        Args:
            file_type: Either "input" or "output"

        Returns:
            Path to the appropriate directory

        Raises:
            ValueError: If file_type is invalid
        """
        if file_type == "input":
            return self._input_dir
        if file_type == "output":
            return self._output_dir
        raise ValueError(f"Invalid file_type: {file_type}. Must be 'input' or 'output'")

    async def _get_session_totals(self) -> tuple[int, int]:
        """Get total file count and size for the session.

        Returns:
            Tuple of (total_files, total_size_bytes)
        """
        # Run blocking file I/O in executor
        loop = asyncio.get_running_loop()

        def _calculate_totals():
            total_files = 0
            total_size = 0
            for file_type in ("input", "output"):
                dir_path = self._get_dir(file_type)
                if dir_path.exists():
                    for file_path in dir_path.iterdir():
                        if file_path.is_file():
                            total_files += 1
                            total_size += file_path.stat().st_size
            return total_files, total_size

        return await loop.run_in_executor(_executor, _calculate_totals)

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal attacks.

        Removes directory separators, special characters, and ensures
        the filename is safe for filesystem storage. Original extension
        is preserved.

        Args:
            filename: Original filename from user input

        Returns:
            Sanitized filename safe for filesystem use

        Examples:
            >>> sanitize_filename("../../etc/passwd")
            "etcpasswd"
            >>> sanitize_filename("my document.pdf")
            "my_document.pdf"
            >>> sanitize_filename("file.txt")
            "file.txt"
        """
        # Extract extension
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
        """Validate file against size and type constraints.

        Args:
            filename: Name of the file to validate
            size: Size of the file in bytes

        Raises:
            FileSizeExceededError: If file exceeds 50MB limit
            InvalidFileTypeError: If file extension is not allowed
            SessionSizeExceededError: If session would exceed 500MB limit
            FileCountExceededError: If session would exceed 100 file limit
        """
        # Check individual file size
        if size > MAX_FILE_SIZE_BYTES:
            raise FileSizeExceededError(
                f"File size ({size} bytes) exceeds maximum allowed "
                f"({MAX_FILE_SIZE_BYTES} bytes = {MAX_FILE_SIZE_BYTES // (1024*1024)}MB)"
            )

        # Check file extension
        ext = Path(filename).suffix.lstrip(".").lower()
        if ext and ext not in ALLOWED_EXTENSIONS:
            allowed_str = ", ".join(sorted(ALLOWED_EXTENSIONS))
            raise InvalidFileTypeError(
                f"File extension '.{ext}' is not allowed. "
                f"Allowed extensions: {allowed_str}"
            )

        # Check session limits
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
        """Guess MIME type from filename extension.

        Args:
            filename: Filename to analyze

        Returns:
            MIME type string (defaults to "application/octet-stream")
        """
        ext = Path(filename).suffix.lstrip(".").lower()
        return MIME_TYPES.get(ext, "application/octet-stream")

    async def _make_safe_name_unique(self, safe_name: str, file_type: Literal["input", "output"]) -> str:
        """Make filename unique within the target directory.

        If a file with the same safe_name exists, appends a counter suffix.

        Args:
            safe_name: Sanitized base filename
            file_type: Target directory type ("input" or "output")

        Returns:
            Unique safe filename
        """
        target_dir = self._get_dir(file_type)
        counter = 0
        unique_name = safe_name

        # Run the existence check in executor to avoid blocking on disk I/O
        loop = asyncio.get_running_loop()

        def check_exists():
            return (target_dir / unique_name).exists()

        while await loop.run_in_executor(_executor, check_exists):
            stem = Path(safe_name).stem
            ext = Path(safe_name).suffix
            counter += 1
            unique_name = f"{stem}_{counter}{ext}"

        return unique_name

    async def save_input_file(self, file: UploadFile, validate: bool = True) -> FileMetadata:
        """Save a user-uploaded file to the input directory.

        Args:
            file: FastAPI UploadFile from multipart form data
            validate: Whether to validate file constraints (default: True)

        Returns:
            FileMetadata object with file information

        Raises:
            FileStorageError: If file operation fails
        """
        if not file.filename:
            raise FileStorageError("Upload file has no filename")

        # Read file content to get size
        content = file.file.read()
        size = len(content)
        original_name = file.filename

        # Debug: log content info
        logger.info(f"DEBUG: Read {size} bytes from upload, type={type(content).__name__}")

        # Validate if requested
        if validate:
            await self.validate_file(original_name, size)

        # Sanitize filename
        safe_name = self.sanitize_filename(original_name)
        safe_name = await self._make_safe_name_unique(safe_name, "input")

        # Write to temp file first for atomic operation
        target_path = self._input_dir / safe_name
        temp_path = target_path.with_suffix(".tmp")

        try:
            # Use asyncio for non-blocking file write
            loop = asyncio.get_running_loop()
            logger.info(f"DEBUG: Writing {len(content)} bytes to {temp_path}")
            await loop.run_in_executor(_executor, _write_file_atomic, temp_path, content)
            logger.info(f"DEBUG: Write completed, temp file size: {temp_path.stat().st_size if temp_path.exists() else 0}")

            # Atomic rename (sync but fast - metadata only)
            temp_path.replace(target_path)

            # Create metadata
            metadata = FileMetadata(
                safe_name=safe_name,
                original_name=original_name,
                file_type="input",
                size_bytes=size,
                content_type=file.content_type or self._guess_content_type(original_name),
                created_at=datetime.now().isoformat(),
                session_id=self._session_id,
            )

            logger.info(
                f"Saved input file: {original_name} -> {safe_name} "
                f"({size} bytes) for session {self._session_id}"
            )
            return metadata

        except IOError as e:
            # Cleanup temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise FileStorageError(f"Failed to save file: {e}") from e
        finally:
            # Reset file pointer for potential re-read
            file.file.seek(0)

    async def save_output_file(
        self, filename: str, content: bytes, validate: bool = True
    ) -> FileMetadata:
        """Save an SDK-generated file to the output directory.

        Args:
            filename: Name for the output file
            content: File content as bytes
            validate: Whether to validate file constraints (default: True)

        Returns:
            FileMetadata object with file information

        Raises:
            FileStorageError: If file operation fails
        """
        size = len(content)

        # Validate if requested
        if validate:
            await self.validate_file(filename, size)

        # Sanitize and make unique
        safe_name = self.sanitize_filename(filename)
        safe_name = await self._make_safe_name_unique(safe_name, "output")

        # Write to temp file first for atomic operation
        target_path = self._output_dir / safe_name
        temp_path = target_path.with_suffix(".tmp")

        try:
            # Use asyncio for non-blocking file write
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(_executor, _write_file_atomic, temp_path, content)

            # Atomic rename (sync but fast - metadata only)
            temp_path.replace(target_path)

            # Create metadata
            metadata = FileMetadata(
                safe_name=safe_name,
                original_name=filename,
                file_type="output",
                size_bytes=size,
                content_type=self._guess_content_type(filename),
                created_at=datetime.now().isoformat(),
                session_id=self._session_id,
            )

            logger.info(
                f"Saved output file: {filename} -> {safe_name} "
                f"({size} bytes) for session {self._session_id}"
            )
            return metadata

        except IOError as e:
            # Cleanup temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise FileStorageError(f"Failed to save output file: {e}") from e

    async def list_files(
        self, file_type: Optional[Literal["input", "output"]] = None
    ) -> list[FileMetadata]:
        """List files in the session storage.

        Args:
            file_type: Filter by file type ("input" or "output").
                       None returns both input and output files.

        Returns:
            List of FileMetadata objects sorted by creation time (newest first)

        Examples:
            >>> storage = FileStorage("user", "sess-1")
            >>> all_files = await storage.list_files()
            >>> inputs = await storage.list_files("input")
        """
        # Run blocking file I/O in executor
        loop = asyncio.get_running_loop()

        def _list_files_sync():
            results = []
            file_types = [file_type] if file_type else ["input", "output"]

            for ft in file_types:
                dir_path = self._get_dir(ft)
                if not dir_path.exists():
                    continue

                for file_path in dir_path.iterdir():
                    if file_path.is_file():
                        stat = file_path.stat()
                        # Try to find original name in a sidecar metadata file
                        # For now, use safe_name as original_name
                        metadata = FileMetadata(
                            safe_name=file_path.name,
                            original_name=file_path.name,  # Could be enhanced with metadata lookup
                            file_type=ft,
                            size_bytes=stat.st_size,
                            content_type=self._guess_content_type(file_path.name),
                            created_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            session_id=self._session_id,
                        )
                        results.append(metadata)

            # Sort by creation time, newest first
            results.sort(key=lambda m: m.created_at, reverse=True)
            return results

        return await loop.run_in_executor(_executor, _list_files_sync)

    async def delete_file(self, safe_name: str, file_type: Literal["input", "output"]) -> bool:
        """Delete a file from storage.

        Args:
            safe_name: Safe filename to delete
            file_type: Either "input" or "output"

        Returns:
            True if file was deleted, False if not found

        Raises:
            ValueError: If file_type is invalid
        """
        dir_path = self._get_dir(file_type)
        file_path = dir_path / safe_name

        # Run blocking file I/O in executor
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
        """Get the filesystem path for a file.

        This method is intended for use by the SDK to read files for tool operations.

        Args:
            safe_name: Safe filename to look up
            file_type: Either "input" or "output"

        Returns:
            Path to the file

        Raises:
            ValueError: If file_type is invalid
            FileNotFound: If file doesn't exist
        """
        dir_path = self._get_dir(file_type)
        file_path = dir_path / safe_name

        if not file_path.exists():
            raise FileNotFound(
                f"File not found: {safe_name} in {file_type} directory "
                f"for session {self._session_id}"
            )

        return file_path


def get_user_file_storage(username: str, session_id: str) -> FileStorage:
    """Get FileStorage instance for a user session.

    Factory function following the pattern of get_user_session_storage.

    Args:
        username: User's username for data isolation
        session_id: Session ID for file grouping

    Returns:
        FileStorage instance for the user's session

    Raises:
        ValueError: If username or session_id is empty
    """
    if not username:
        raise ValueError("Username is required for file storage access")
    if not session_id:
        raise ValueError("Session ID is required for file storage access")

    return FileStorage(username=username, session_id=session_id)


def delete_session_files(username: str, session_id: str, base_path: str = "data") -> bool:
    """Delete the entire file storage directory for a session.

    Removes data/{username}/files/{session_id}/ and all its contents.

    Args:
        username: User's username
        session_id: Session ID whose files to delete
        base_path: Base directory for file storage (default: "data")

    Returns:
        True if directory was deleted, False if it didn't exist
    """
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
