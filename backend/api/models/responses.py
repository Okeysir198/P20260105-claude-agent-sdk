"""Response models for FastAPI endpoints."""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


class SessionResponse(BaseModel):
    """Response model for session creation.

    Attributes:
        session_id: Unique identifier for the session
        status: Current status of the session
        resumed: Whether this session was resumed from a previous one
    """

    session_id: str = Field(
        ...,
        description="Unique identifier for the session"
    )
    status: str = Field(
        ...,
        description="Current status of the session (e.g., 'active', 'pending')"
    )
    resumed: bool = Field(
        default=False,
        description="Whether this session was resumed from a previous one"
    )


class SessionInfo(BaseModel):
    """Response model for session information.

    Attributes:
        session_id: Unique identifier for the session
        name: Custom name for the session
        first_message: The first message sent in the session
        created_at: ISO timestamp of when the session was created
        turn_count: Number of conversation turns in the session
        user_id: Optional user ID for multi-user tracking
    """

    session_id: str = Field(
        ...,
        description="Unique identifier for the session"
    )
    name: str | None = Field(
        default=None,
        description="Custom name for the session"
    )
    first_message: str | None = Field(
        default=None,
        description="The first message sent in the session"
    )
    created_at: str = Field(
        ...,
        description="ISO timestamp of when the session was created"
    )
    turn_count: int = Field(
        ...,
        ge=0,
        description="Number of conversation turns in the session"
    )
    user_id: str | None = Field(
        default=None,
        description="Optional user ID for multi-user tracking"
    )
    agent_id: str | None = Field(
        default=None,
        description="Agent ID associated with the session"
    )
    cwd_id: str | None = Field(
        default=None,
        description="File storage directory ID"
    )
    permission_folders: list[str] | None = Field(
        default=None,
        description="Allowed write directories"
    )


class ErrorResponse(BaseModel):
    """Response model for error responses.

    Attributes:
        error: Error type or category
        detail: Detailed error message or additional information
    """

    error: str = Field(
        ...,
        description="Error type or category"
    )
    detail: str | None = Field(
        default=None,
        description="Detailed error message or additional information"
    )


class CloseSessionResponse(BaseModel):
    """Response model for closing a session.

    Attributes:
        status: Status confirmation
    """

    status: str = Field(
        ...,
        description="Status confirmation (e.g., 'closed')"
    )


class DeleteSessionResponse(BaseModel):
    """Response model for deleting a session.

    Attributes:
        status: Status confirmation
    """

    status: str = Field(
        ...,
        description="Status confirmation (e.g., 'deleted')"
    )


class SessionHistoryResponse(BaseModel):
    """Response model for session history.

    Attributes:
        session_id: Unique identifier for the session
        messages: List of messages in the conversation (may be empty)
        turn_count: Number of conversation turns
        first_message: The first message in the session
    """

    session_id: str = Field(
        ...,
        description="Unique identifier for the session"
    )
    messages: list = Field(
        default_factory=list,
        description="List of messages in the conversation history"
    )
    turn_count: int = Field(
        default=0,
        ge=0,
        description="Number of conversation turns in the session"
    )
    first_message: str | None = Field(
        default=None,
        description="The first message sent in the session"
    )


class SearchResultResponse(BaseModel):
    """Response model for a single search result.

    Attributes:
        session_id: Unique identifier for the session
        name: Custom name for the session
        first_message: The first message sent in the session
        created_at: ISO timestamp of when the session was created
        turn_count: Number of conversation turns in the session
        agent_id: Agent ID associated with the session
        relevance_score: Relevance score (0-1)
        match_count: Number of query matches found
        snippet: Text snippet showing match context
    """

    session_id: str = Field(
        ...,
        description="Unique identifier for the session"
    )
    name: str | None = Field(
        default=None,
        description="Custom name for the session"
    )
    first_message: str | None = Field(
        default=None,
        description="The first message sent in the session"
    )
    created_at: str = Field(
        ...,
        description="ISO timestamp of when the session was created"
    )
    turn_count: int = Field(
        ...,
        ge=0,
        description="Number of conversation turns in the session"
    )
    agent_id: str | None = Field(
        default=None,
        description="Agent ID associated with the session"
    )
    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relevance score from 0 to 1"
    )
    match_count: int = Field(
        ...,
        ge=0,
        description="Number of query matches found in session"
    )
    snippet: str | None = Field(
        default=None,
        description="Text snippet showing match context"
    )


class SearchResponse(BaseModel):
    """Response model for search results.

    Attributes:
        results: List of search results matching the query
        total_count: Total number of results found
        query: The search query string
    """

    results: list[SearchResultResponse] = Field(
        default_factory=list,
        description="List of search results matching the query"
    )
    total_count: int = Field(
        ...,
        ge=0,
        description="Total number of results found"
    )
    query: str = Field(
        ...,
        description="The search query string"
    )


class FileMetadata(BaseModel):
    """Response model for file metadata.

    Attributes:
        safe_name: Sanitized filename (used for storage)
        original_name: Original filename from upload
        file_type: Type of file (input or output)
        size_bytes: File size in bytes
        content_type: MIME type of the file
        created_at: ISO timestamp when file was created
        session_id: Session ID file belongs to
    """

    safe_name: str = Field(
        ...,
        description="Sanitized filename (used for storage)"
    )
    original_name: str = Field(
        ...,
        description="Original filename from upload"
    )
    file_type: Literal["input", "output"] = Field(
        ...,
        description="Type of file (input or output)"
    )
    size_bytes: int = Field(
        ...,
        ge=0,
        description="File size in bytes"
    )

    def __str__(self) -> str:
        return f"FileMetadata(safe_name=\"{self.safe_name}\", original_name=\"{self.original_name}\")"

    content_type: str = Field(
        ...,
        description="MIME type of the file"
    )
    created_at: str = Field(
        ...,
        description="ISO timestamp when file was created"
    )

    model_config = dict(arbitrary_types_allowed=True)
    session_id: str = Field(
        ...,
        description="Session ID file belongs to"
    )


class FileUploadResponse(BaseModel):
    """Response model for file upload.

    Attributes:
        success: Whether the upload was successful
        file: File metadata if successful
        error: Error message if failed
        total_files: Total number of files in session after upload
        total_size_bytes: Total size of all files in bytes
    """

    success: bool = Field(
        ...,
        description="Whether the upload was successful"
    )
    file: Optional[FileMetadata] = Field(
        default=None,
        description="File metadata if successful"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if failed"
    )
    total_files: int = Field(
        ...,
        ge=0,
        description="Total number of files in session after upload"
    )
    total_size_bytes: int = Field(
        ...,
        ge=0,
        description="Total size of all files in bytes"
    )


class FileListResponse(BaseModel):
    """Response model for file list.

    Attributes:
        session_id: Session ID files belong to
        files: List of file metadata objects
        total_files: Total number of files
        total_size_bytes: Total size of all files in bytes
    """

    session_id: str = Field(
        ...,
        description="Session ID files belong to"
    )
    files: List[FileMetadata] = Field(
        default_factory=list,
        description="List of file metadata objects"
    )
    total_files: int = Field(
        ...,
        ge=0,
        description="Total number of files"
    )
    total_size_bytes: int = Field(
        ...,
        ge=0,
        description="Total size of all files in bytes"
    )


class FileDeleteResponse(BaseModel):
    """Response model for file deletion.

    Attributes:
        success: Whether the deletion was successful
        error: Error message if failed
        remaining_files: Number of files remaining after deletion
    """

    success: bool = Field(
        ...,
        description="Whether the deletion was successful"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if failed"
    )
    remaining_files: int = Field(
        ...,
        ge=0,
        description="Number of files remaining after deletion"
    )
