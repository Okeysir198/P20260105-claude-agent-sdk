"""Attachment utilities: MIME detection, size validation, and path resolution."""

import mimetypes
import os
from pathlib import Path


def _guess_mime_type(filename: str) -> str:
    """Auto-detect MIME type from file extension."""
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"


def validate_attachment_size(file_path: str, max_size_mb: int = 25) -> bool:
    """Check file size is within limits. Raises FileNotFoundError or ValueError."""
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
    attachments: list[dict],
    username: str,
    session_id: str | None = None,
) -> list[dict]:
    """Resolve file paths from user input with security checks.

    Each attachment dict must contain either:
    - {"path": "/absolute/path"}: Direct absolute path
    - {"filename": "doc.pdf"}: Filename to search in session directories

    Returns list of dicts with path, filename, and mime_type keys.
    """
    if not attachments:
        return []

    user_data_dir = Path(os.getcwd()) / "data" / username
    resolved = []

    for attachment in attachments:
        if not isinstance(attachment, dict):
            raise ValueError(f"Invalid attachment format: must be dict, got {type(attachment)}")

        if "path" in attachment:
            file_path = attachment["path"]
            filename = os.path.basename(file_path)
            abs_path = os.path.abspath(file_path)

            if not os.path.isfile(abs_path):
                raise FileNotFoundError(f"Attachment file not found: {file_path}")

        elif "filename" in attachment:
            filename = attachment["filename"]

            if not session_id:
                raise ValueError(
                    "session_id is required when using filename-only attachments. "
                    "Provide session_id or use absolute path with 'path' key."
                )

            search_dirs = [
                user_data_dir / "files" / session_id / "input",
                user_data_dir / "files" / session_id / "output",
            ]

            abs_path = None
            for search_dir in search_dirs:
                resolved_candidate = os.path.abspath(search_dir / filename)
                if resolved_candidate.startswith(str(search_dir)) and os.path.isfile(resolved_candidate):
                    abs_path = resolved_candidate
                    break

            if not abs_path:
                raise FileNotFoundError(
                    f"Attachment file '{filename}' not found in session directories: "
                    f"{[str(d) for d in search_dirs]}"
                )

        else:
            raise ValueError(
                "Attachment must contain either 'path' (absolute path) or 'filename' key"
            )

        validate_attachment_size(abs_path)

        resolved.append({
            "path": abs_path,
            "filename": filename,
            "mime_type": _guess_mime_type(filename),
        })

    return resolved
