"""File management endpoints.

Provides REST API for uploading, listing, downloading, and deleting
session files. All endpoints require authentication and validate session
ownership before allowing file operations.
"""
import logging
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse

from agent.core.storage import get_user_session_storage
from api.core.errors import InvalidRequestError, SessionNotFoundError
from api.dependencies.auth import get_current_user
from api.models.requests import DeleteFileRequest
from api.models.responses import (
    FileDeleteResponse,
    FileListResponse,
    FileMetadata,
    FileUploadResponse,
)
from api.models.user_auth import UserTokenPayload
from api.services.file_download_token import validate_download_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])

# Maximum file upload size (50MB)
MAX_UPLOAD_SIZE = 50 * 1024 * 1024


async def _validate_session_ownership(
    session_id: str,
    username: str
) -> str:
    """Validate that the user owns the session and return its cwd_id.

    Args:
        session_id: Session ID to validate
        username: Username from JWT token

    Returns:
        The session's cwd_id for file storage (falls back to session_id for old sessions)

    Raises:
        SessionNotFoundError: If session not found or user doesn't own it
    """
    session_storage = get_user_session_storage(username)
    session = session_storage.get_session(session_id)

    if not session:
        logger.warning(f"Session '{session_id}' not found for user '{username}'")
        raise SessionNotFoundError(session_id)

    return session.cwd_id or session_id


def _get_mime_type(file_path: Path) -> str:
    """Get MIME type for a file.

    Args:
        file_path: Path to the file

    Returns:
        MIME type string, defaults to 'application/octet-stream'
    """
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type or "application/octet-stream"


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload a file to a session",
    description="Upload a file to the input directory of a session"
)
async def upload_file(
    file: UploadFile = File(..., description="File to upload"),
    session_id: str = Form(..., description="Session ID to associate file with"),
    user: UserTokenPayload = Depends(get_current_user)
) -> FileUploadResponse:
    """Upload a file to the session's input directory.

    Args:
        file: File to upload
        session_id: Session ID to associate file with
        user: Authenticated user from token

    Returns:
        FileUploadResponse with file details

    Raises:
        SessionNotFoundError: If session not found or user doesn't own it
        InvalidRequestError: If file validation fails
        HTTPException: If file size exceeds limit
    """
    from agent.core.file_storage import FileStorage

    # Validate user owns session and get cwd_id for file storage
    cwd_id = await _validate_session_ownership(session_id, user.username)

    # Validate file size
    file_content = await file.read()
    if len(file_content) > MAX_UPLOAD_SIZE:
        return FileUploadResponse(
            success=False,
            file=None,
            error=f"File size exceeds maximum allowed size of {MAX_UPLOAD_SIZE} bytes",
            total_files=0,
            total_size_bytes=0
        )

    # Save file using FileStorage with cwd_id directory
    file_storage = FileStorage(username=user.username, session_id=cwd_id)

    try:
        metadata = await file_storage.save_input_file(
            content=file_content,
            filename=file.filename or "unnamed",
            content_type=file.content_type or "application/octet-stream",
        )
        safe_name = metadata.safe_name
        original_name = metadata.original_name
    except ValueError as e:
        return FileUploadResponse(
            success=False,
            file=None,
            error=str(e),
            total_files=0,
            total_size_bytes=0
        )

    logger.info(
        f"File uploaded: user={user.username}, session={session_id}, "
        f"file={original_name} (safe={safe_name}), size={len(file_content)}"
    )

    # Get file stats for total calculation
    all_files = await file_storage.list_files()
    total_files = len(all_files)
    total_size = sum(f.size_bytes for f in all_files)

    return FileUploadResponse(
        success=True,
        file=FileMetadata(
            safe_name=safe_name,
            original_name=original_name,
            file_type="input",
            size_bytes=len(file_content),
            content_type=file.content_type or "application/octet-stream",
            created_at=datetime.now().isoformat() + "Z",
            session_id=session_id,
        ),
        error=None,
        total_files=total_files,
        total_size_bytes=total_size,
    )


@router.get(
    "/{session_id}/list",
    response_model=FileListResponse,
    summary="List files for a session",
    description="List all files for a session, optionally filtered by type"
)
async def list_files(
    session_id: str,
    file_type: Optional[Literal["input", "output"]] = None,
    user: UserTokenPayload = Depends(get_current_user)
) -> FileListResponse:
    """List files for a session.

    Args:
        session_id: Session ID to list files for
        file_type: Optional filter by file type (input or output)
        user: Authenticated user from token

    Returns:
        FileListResponse with list of files

    Raises:
        SessionNotFoundError: If session not found or user doesn't own it
    """
    from agent.core.file_storage import FileStorage

    # Validate user owns session and get cwd_id for file storage
    cwd_id = await _validate_session_ownership(session_id, user.username)

    # List files using FileStorage with cwd_id directory
    file_storage = FileStorage(username=user.username, session_id=cwd_id)

    try:
        files = await file_storage.list_files(file_type=file_type)
    except ValueError as e:
        raise InvalidRequestError(message=str(e))

    # Convert file_storage.FileMetadata objects to Pydantic FileMetadata models
    file_metadata_list = [
        FileMetadata(
            safe_name=f.safe_name,
            original_name=f.original_name,
            file_type=f.file_type,  # type: ignore[arg-type]
            size_bytes=f.size_bytes,
            content_type=f.content_type,
            created_at=f.created_at,
            session_id=f.session_id,
        )
        for f in files
    ]

    total_size = sum(f.size_bytes for f in file_metadata_list)

    return FileListResponse(
        session_id=session_id,
        files=file_metadata_list,
        total_files=len(file_metadata_list),
        total_size_bytes=total_size,
    )


@router.get(
    "/{session_id}/download/{file_type}/{safe_name}",
    summary="Download a file",
    description="Download a file from a session's input or output directory"
)
async def download_file(
    session_id: str,
    file_type: Literal["input", "output"],
    safe_name: str,
    user: UserTokenPayload = Depends(get_current_user)
) -> FileResponse:
    """Download a file from a session.

    Args:
        session_id: Session ID the file belongs to
        file_type: Type of file (input or output)
        safe_name: Safe filename (uuid + original name)
        user: Authenticated user from token

    Returns:
        FileResponse with the file content

    Raises:
        SessionNotFoundError: If session not found or user doesn't own it
        InvalidRequestError: If file not found
    """
    from agent.core.file_storage import FileStorage

    # Validate user owns session and get cwd_id for file storage
    cwd_id = await _validate_session_ownership(session_id, user.username)

    # Validate file_type
    if file_type not in ("input", "output"):
        raise InvalidRequestError(
            message=f"Invalid file_type: {file_type}. Must be 'input' or 'output'"
        )

    # Get file path using FileStorage with cwd_id directory
    file_storage = FileStorage(username=user.username, session_id=cwd_id)

    try:
        file_path = file_storage.get_file_path(safe_name=safe_name, file_type=file_type)
    except FileNotFoundError as e:
        raise InvalidRequestError(message=str(e))

    if not file_path.exists():
        logger.warning(
            f"File not found: user={user.username}, session={session_id}, "
            f"type={file_type}, file={safe_name}"
        )
        raise InvalidRequestError(
            message=f"File '{safe_name}' not found in {file_type} directory"
        )

    # Get MIME type
    mime_type = _get_mime_type(file_path)

    logger.info(
        f"File downloaded: user={user.username}, session={session_id}, "
        f"type={file_type}, file={safe_name}"
    )

    return FileResponse(
        path=str(file_path),
        media_type=mime_type,
        filename=file_path.name,
        headers={
            "Content-Disposition": f'attachment; filename="{file_path.name}"'
        }
    )


@router.delete(
    "/{session_id}/delete",
    response_model=FileDeleteResponse,
    summary="Delete a file",
    description="Delete a file from a session's input or output directory"
)
async def delete_file(
    session_id: str,
    request: DeleteFileRequest,
    user: UserTokenPayload = Depends(get_current_user)
) -> FileDeleteResponse:
    """Delete a file from a session.

    Args:
        session_id: Session ID the file belongs to
        request: Delete request with safe_name and file_type
        user: Authenticated user from token

    Returns:
        FileDeleteResponse confirming deletion

    Raises:
        SessionNotFoundError: If session not found or user doesn't own it
        InvalidRequestError: If file not found or file_type invalid
    """
    from agent.core.file_storage import FileStorage

    # Validate user owns session and get cwd_id for file storage
    cwd_id = await _validate_session_ownership(session_id, user.username)

    # Delete file using FileStorage with cwd_id directory
    file_storage = FileStorage(username=user.username, session_id=cwd_id)

    try:
        deleted = await file_storage.delete_file(
            safe_name=request.safe_name,
            file_type=request.file_type
        )
    except (FileNotFoundError, ValueError) as e:
        return FileDeleteResponse(
            success=False,
            error=str(e),
            remaining_files=0
        )

    if not deleted:
        return FileDeleteResponse(
            success=False,
            error=f"File '{request.safe_name}' not found or already deleted",
            remaining_files=0
        )

    logger.info(
        f"File deleted: user={user.username}, session={session_id}, "
        f"type={request.file_type}, file={request.safe_name}"
    )

    # Get remaining files count
    try:
        all_files = await file_storage.list_files()
        remaining = len(all_files)
    except Exception:
        remaining = 0

    return FileDeleteResponse(
        success=True,
        error=None,
        remaining_files=remaining
    )


@router.get(
    "/dl/{token:path}",
    summary="Download a file via signed token",
    description="Public endpoint — the signed token is the credential. No API key or JWT needed."
)
async def download_file_by_token(token: str) -> FileResponse:
    """Download a file using a pre-signed download token.

    The token encodes the username, session cwd_id, file path, and expiry.
    Returns 404 for invalid, expired, or tampered tokens (no info leakage).
    """
    claim = validate_download_token(token)
    if not claim:
        raise HTTPException(status_code=404, detail="Not found")

    # The relative_path from the token is relative to session_cwd
    # session_cwd is: data/{username}/sessions/{cwd_id}
    data_dir = os.environ.get("DATA_DIR", str(Path(__file__).parent.parent.parent / "data"))
    session_dir = Path(data_dir) / claim.username / "sessions" / claim.cwd_id
    file_path = (session_dir / claim.relative_path).resolve()

    # Security: ensure resolved path is within session directory
    session_dir_resolved = session_dir.resolve()
    if not str(file_path).startswith(str(session_dir_resolved) + "/") and file_path != session_dir_resolved:
        raise HTTPException(status_code=404, detail="Not found")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Not found")

    mime_type = _get_mime_type(file_path)

    return FileResponse(
        path=str(file_path),
        media_type=mime_type,
        filename=file_path.name,
        headers={
            "Content-Disposition": f'attachment; filename="{file_path.name}"',
            "X-Content-Type-Options": "nosniff",
        }
    )
