"""Send file to chat tool implementation.

Validates a file in the session directory and returns structured metadata.
The platform worker intercepts the result to deliver the file via the platform adapter.
"""
import mimetypes
from typing import Any

from claude_agent_sdk import tool

from .helpers import (
    get_session_context,
    handle_media_service_errors,
    make_tool_error,
    make_tool_result,
    sanitize_file_path,
)


@tool(
    name="send_file_to_chat",
    description=(
        "Send a file from the session directory to the user's chat. "
        "Use this to deliver generated files (audio, images, documents, etc.) directly to the user. "
        "The file must exist in the session directory (input/, output/, or root).\n\n"
        "**Parameters:**\n"
        "- file_path: Relative path within the session directory "
        "(e.g., 'output/tts_123.wav', 'input/document.pdf', 'report.txt')"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": (
                    "Relative path to the file within the session directory. "
                    "Supports files in output/, input/, or the root session directory. "
                    "Examples: 'output/tts_123.wav', 'input/photo.jpg', 'result.csv'"
                ),
            },
        },
        "required": ["file_path"],
    },
)
@handle_media_service_errors("send_file")
async def send_file_to_chat(inputs: dict[str, Any]) -> dict[str, Any]:
    """Validate a file in the session directory and return delivery metadata."""
    file_path = inputs.get("file_path", "")
    if not file_path:
        return make_tool_error("file_path is required.")

    username, file_storage = get_session_context()
    session_id = file_storage._session_id
    session_dir = file_storage.get_session_dir()

    # Strip session_id prefix if the agent passes "cwd_id/output/file.wav"
    # (media tools return paths like "session_id/output/filename")
    if file_path.startswith(session_id + "/"):
        file_path = file_path[len(session_id) + 1:]

    # Sanitize and resolve within session directory
    full_path = sanitize_file_path(file_path, session_dir)

    if not full_path.exists():
        return make_tool_error(f"File not found: {file_path}")

    if not full_path.is_file():
        return make_tool_error(f"Path is not a file: {file_path}")

    # File metadata
    filename = full_path.name
    size_bytes = full_path.stat().st_size
    mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    # Build download URL
    # Compute relative path from session root for the download token
    rel_from_session = str(full_path.resolve().relative_to(session_dir.resolve()))
    relative_path_for_token = f"{session_id}/{rel_from_session}"

    from api.services.file_download_token import create_download_token, build_download_url

    token = create_download_token(
        username=username,
        cwd_id=session_id,
        relative_path=relative_path_for_token,
        expire_hours=24,
    )
    download_url = build_download_url(token)

    # Determine content type for frontend rendering
    def determine_content_type(mime: str) -> str:
        """Map MIME type to content block type."""
        if mime.startswith('audio/'):
            return 'audio'
        elif mime.startswith('video/'):
            return 'video'
        elif mime.startswith('image/'):
            return 'image'
        else:
            return 'file'

    content_type = determine_content_type(mime_type)

    return make_tool_result({
        "action": "deliver_file",
        "file_path": rel_from_session,
        "filename": filename,
        "mime_type": mime_type,
        "size_bytes": size_bytes,
        "download_url": download_url,
        "_standalone_file": {  # Signals frontend to create separate message
            "type": content_type,
            "url": download_url,
            "filename": filename,
            "mime_type": mime_type,
            "size_bytes": size_bytes
        }
    })


__all__ = ["send_file_to_chat"]
