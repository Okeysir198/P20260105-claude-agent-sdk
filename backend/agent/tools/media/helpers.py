"""Shared utilities for media processing tools.

Provides path sanitization, file validation, service health checks,
MCP result formatting, and download URL creation used across OCR, STT, and TTS tools.
"""
import json
import logging
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def sanitize_file_path(file_path: str, base_dir: Path) -> Path:
    """Sanitize and resolve a file path, preventing path traversal.

    Args:
        file_path: User-provided file path (e.g., 'document.pdf')
        base_dir: Base directory the path must stay within

    Returns:
        Resolved absolute path within base_dir

    Raises:
        ValueError: If path attempts traversal outside base_dir
    """
    # Normalize and resolve
    resolved = (base_dir / file_path).resolve()

    # Ensure the resolved path is within the base directory
    base_resolved = base_dir.resolve()
    if not str(resolved).startswith(str(base_resolved) + "/") and resolved != base_resolved:
        raise ValueError(f"Path traversal detected: '{file_path}' resolves outside allowed directory")

    return resolved


def validate_file_format(file_path: Path, allowed_formats: list[str], tool_name: str) -> None:
    """Validate that file has an allowed format extension.

    Args:
        file_path: Path to validate
        allowed_formats: List of allowed extensions (without dots, e.g. ['pdf', 'png'])
        tool_name: Tool name for error messages

    Raises:
        ValueError: If file format is not allowed
    """
    ext = file_path.suffix.lstrip(".").lower()
    if ext not in allowed_formats:
        raise ValueError(
            f"Unsupported file format '.{ext}' for {tool_name}. "
            f"Allowed formats: {', '.join(allowed_formats)}"
        )


def make_tool_result(data: dict[str, Any]) -> dict[str, Any]:
    """Wrap a result dict in MCP-compliant tool result format.

    The Claude Agent SDK expects tool results as:
    {"content": [{"type": "text", "text": "<json string>"}]}

    Args:
        data: Result dict to serialize as JSON text content.

    Returns:
        MCP-compatible tool result dict.
    """
    return {"content": [{"type": "text", "text": json.dumps(data)}]}


def make_tool_error(message: str) -> dict[str, Any]:
    """Create an MCP-compliant error result.

    Args:
        message: Error description.

    Returns:
        MCP-compatible error result dict with is_error=True.
    """
    return {"content": [{"type": "text", "text": message}], "is_error": True}


async def check_service_health(url: str, timeout: float = 2.0) -> str:
    """Check if a service is available.

    Args:
        url: Base URL of the service
        timeout: Connection timeout in seconds

    Returns:
        "available" if service responds, "unavailable" otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{url}/health")
            if response.status_code == 200:
                return "available"
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, Exception):
        pass
    return "unavailable"
