"""Send file to chat tool implementation."""
import mimetypes
from typing import Any

from .download_token import create_download_token, build_download_url
from .helpers import (
    get_session_context,
    handle_media_service_errors,
    make_tool_error,
    make_tool_result,
    sanitize_file_path,
)


def _content_type_from_mime(mime: str) -> str:
    """Map MIME type to content block type for frontend rendering."""
    prefix = mime.split("/")[0]
    if prefix in ("audio", "video", "image"):
        return prefix
    return "file"


@handle_media_service_errors("send_file")
async def send_file_to_chat(inputs: dict[str, Any]) -> dict[str, Any]:
    """Validate a file in the session directory and return delivery metadata."""
    file_path = inputs.get("file_path", "")
    if not file_path:
        return make_tool_error("file_path is required.")

    username, file_storage = get_session_context()
    session_id = file_storage._session_id
    session_dir = file_storage.get_session_dir()

    # Strip session_id prefix (media tools return paths like "session_id/output/filename")
    if file_path.startswith(session_id + "/"):
        file_path = file_path[len(session_id) + 1:]

    full_path = sanitize_file_path(file_path, session_dir)

    if not full_path.exists():
        return make_tool_error(f"File not found: {file_path}")

    if not full_path.is_file():
        return make_tool_error(f"Path is not a file: {file_path}")

    filename = full_path.name
    size_bytes = full_path.stat().st_size
    mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    rel_from_session = str(full_path.resolve().relative_to(session_dir.resolve()))
    relative_path_for_token = f"{session_id}/{rel_from_session}"

    token = create_download_token(
        username=username,
        cwd_id=session_id,
        relative_path=relative_path_for_token,
        expire_hours=24,
    )
    download_url = build_download_url(token)
    content_type = _content_type_from_mime(mime_type)

    return make_tool_result({
        "action": "deliver_file",
        "file_path": rel_from_session,
        "filename": filename,
        "mime_type": mime_type,
        "size_bytes": size_bytes,
        "download_url": download_url,
        "_standalone_file": {
            "type": content_type,
            "url": download_url,
            "filename": filename,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
        },
    })


__all__ = ["send_file_to_chat"]
