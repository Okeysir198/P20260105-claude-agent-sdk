"""Shared utilities for media processing tools.

Path sanitization, file validation, service health checks, and MCP result formatting.
"""
from __future__ import annotations

import functools
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent.core.file_storage import FileStorage

import httpx

logger = logging.getLogger(__name__)


def sanitize_file_path(file_path: str, base_dir: Path) -> Path:
    """Resolve file_path within base_dir, raising ValueError on path traversal."""
    resolved = (base_dir / file_path).resolve()
    base_resolved = base_dir.resolve()
    if not str(resolved).startswith(str(base_resolved) + "/") and resolved != base_resolved:
        raise ValueError(f"Path traversal detected: '{file_path}' resolves outside allowed directory")
    return resolved


def validate_file_format(file_path: Path, allowed_formats: list[str], tool_name: str) -> None:
    """Raise ValueError if file extension is not in allowed_formats."""
    ext = file_path.suffix.lstrip(".").lower()
    if ext not in allowed_formats:
        raise ValueError(
            f"Unsupported file format '.{ext}' for {tool_name}. "
            f"Allowed formats: {', '.join(allowed_formats)}"
        )


def make_tool_result(data: dict[str, Any]) -> dict[str, Any]:
    """Wrap a result dict as MCP-compliant tool result (JSON text content)."""
    return {"content": [{"type": "text", "text": json.dumps(data)}]}


def make_tool_error(message: str) -> dict[str, Any]:
    """Create an MCP-compliant error result with is_error=True."""
    return {"content": [{"type": "text", "text": message}], "is_error": True}


async def check_service_health(url: str, timeout: float = 2.0) -> str:
    """Return "available" if service responds at /health, "unavailable" otherwise."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{url}/health")
            if response.status_code == 200:
                return "available"
    except Exception:
        pass
    return "unavailable"


def get_session_context() -> tuple[str, "FileStorage"]:
    """Get username and FileStorage from the current MCP context."""
    from .mcp_server import get_username, get_session_id
    from agent.core.file_storage import FileStorage

    username = get_username()
    session_id = get_session_id()
    return username, FileStorage(username=username, session_id=session_id)


def resolve_input_file(
    file_path: str,
    file_storage: "FileStorage",
    allowed_formats: list[str],
    tool_name: str,
) -> Path:
    """Resolve, validate, and check existence of an input file within the session directory."""
    input_dir = file_storage.get_session_dir() / "input"
    full_path = sanitize_file_path(file_path, input_dir)
    validate_file_format(full_path, allowed_formats, tool_name)

    if not full_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    return full_path


async def save_output_and_build_url(
    file_storage: "FileStorage",
    username: str,
    session_id: str,
    output_filename: str,
    content: bytes,
    expire_hours: int = 24,
) -> tuple[str, str]:
    """Save output file and return (relative_path, signed_download_url)."""
    from api.services.file_download_token import create_download_token, build_download_url

    metadata = await file_storage.save_output_file(output_filename, content)
    relative_path = f"{session_id}/output/{metadata.safe_name}"
    token = create_download_token(
        username=username,
        cwd_id=session_id,
        relative_path=relative_path,
        expire_hours=expire_hours,
    )
    download_url = build_download_url(token)
    return relative_path, download_url


def handle_media_service_errors(service_name: str):
    """Decorator that wraps media tool functions with consistent error handling.

    Catches ValueError, FileNotFoundError, httpx connection/timeout/status errors,
    and unexpected exceptions, returning appropriate MCP error results.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(inputs: dict[str, Any]) -> dict[str, Any]:
            try:
                return await func(inputs)
            except (ValueError, FileNotFoundError) as e:
                return make_tool_error(str(e))
            except httpx.ConnectError:
                return make_tool_error(
                    f"Cannot connect to {service_name} service. Is the Docker container running?"
                )
            except httpx.TimeoutException:
                return make_tool_error(
                    f"{service_name} service timed out (120s). Input may be too large."
                )
            except httpx.HTTPStatusError as e:
                return make_tool_error(
                    f"{service_name} service error: {e.response.status_code}"
                )
            except Exception as e:
                logger.exception(f"Unexpected error in {func.__name__}")
                return make_tool_error(f"Unexpected error: {e}")
        return wrapper
    return decorator
