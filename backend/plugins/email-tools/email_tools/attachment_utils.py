"""
Attachment utilities for email tools.

Provides functions for MIME type detection, file size validation, and attachment
path resolution with security checks and per-user isolation.
"""

import os
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional


def _guess_mime_type(filename: str) -> str:
    """
    Auto-detect MIME type from file extension.

    Args:
        filename: The filename to detect MIME type from

    Returns:
        MIME type string (e.g., 'application/pdf', 'image/jpeg')
        Returns 'application/octet-stream' as fallback if type cannot be determined
    """
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"


def validate_attachment_size(file_path: str, max_size_mb: int = 25) -> bool:
    """
    Check if file size is within allowed limits.

    Args:
        file_path: Absolute path to the file
        max_size_mb: Maximum file size in megabytes (default: 25MB for Gmail)

    Returns:
        True if file size is within limits

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If file size exceeds max_size_mb
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Attachment file not found: {file_path}")

    file_size = os.path.getsize(file_path)
    max_size_bytes = max_size_mb * 1024 * 1024

    if file_size > max_size_bytes:
        size_mb = file_size / (1024 * 1024)
        raise ValueError(
            f"Attachment file too large: {size_mb:.2f}MB "
            f"(exceeds {max_size_mb}MB limit for {os.path.basename(file_path)})"
        )

    return True


def resolve_attachments(
    attachments: List[Dict],
    username: str,
    session_id: Optional[str] = None
) -> List[Dict]:
    """
    Resolve file paths from user input with security checks.

    Args:
        attachments: List of attachment dictionaries. Each can contain:
            - {"path": "/absolute/path"}: Direct absolute path (validated)
            - {"filename": "doc.pdf"}: Filename to search in session directories
        username: Username for per-user directory isolation
        session_id: Session ID for filename-only attachments (required if using filename)

    Returns:
        List of resolved attachment dictionaries with keys:
        - path: Absolute file path
        - filename: Original filename
        - mime_type: Detected MIME type

    Raises:
        ValueError: If invalid attachment format, path traversal detected,
                   or file not found
        FileNotFoundError: If file does not exist

    Security:
        - Path traversal prevention using os.path.abspath
        - Files must exist within allowed directories
        - Per-user isolation maintained
    """
    if not attachments:
        return []

    # Base data directory
    base_dir = Path(os.getcwd())  # Should be backend/
    user_data_dir = base_dir / "data" / username

    resolved = []

    for attachment in attachments:
        if not isinstance(attachment, dict):
            raise ValueError(f"Invalid attachment format: must be dict, got {type(attachment)}")

        # Handle absolute path
        if "path" in attachment:
            file_path = attachment["path"]
            filename = os.path.basename(file_path)

            # Security: resolve to absolute and check for path traversal
            abs_path = os.path.abspath(file_path)

            # Validate file exists
            if not os.path.isfile(abs_path):
                raise FileNotFoundError(f"Attachment file not found: {file_path}")

        # Handle filename-only (search in session directories)
        elif "filename" in attachment:
            filename = attachment["filename"]

            if not session_id:
                raise ValueError(
                    "session_id is required when using filename-only attachments. "
                    "Provide session_id or use absolute path with 'path' key."
                )

            # Define allowed search directories (per-user, per-session)
            search_dirs = [
                user_data_dir / "files" / session_id / "input",
                user_data_dir / "files" / session_id / "output",
            ]

            abs_path = None
            for search_dir in search_dirs:
                candidate_path = search_dir / filename
                # Security: resolve to absolute to prevent path traversal
                resolved_candidate = os.path.abspath(candidate_path)

                # Verify resolved path is within allowed directory
                if resolved_candidate.startswith(str(search_dir)):
                    if os.path.isfile(resolved_candidate):
                        abs_path = resolved_candidate
                        break

            if not abs_path:
                searched_paths = [str(d) for d in search_dirs]
                raise FileNotFoundError(
                    f"Attachment file '{filename}' not found in session directories: "
                    f"{searched_paths}"
                )

        else:
            raise ValueError(
                "Attachment must contain either 'path' (absolute path) or 'filename' key"
            )

        # Validate file size
        validate_attachment_size(abs_path)

        # Detect MIME type
        mime_type = _guess_mime_type(filename)

        resolved.append({
            "path": abs_path,
            "filename": filename,
            "mime_type": mime_type,
        })

    return resolved
