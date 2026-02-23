"""Response models for FastAPI endpoints."""

from typing import Literal

from pydantic import BaseModel, Field


class SessionResponse(BaseModel):
    """Response model for session creation."""

    session_id: str = Field(..., description="Unique identifier for the session")
    status: str = Field(..., description="Current status of the session")
    resumed: bool = Field(default=False, description="Whether this session was resumed")


class SessionInfo(BaseModel):
    """Response model for session information."""

    session_id: str = Field(..., description="Unique identifier for the session")
    name: str | None = Field(default=None, description="Custom name for the session")
    first_message: str | None = Field(default=None, description="The first message sent in the session")
    created_at: str = Field(..., description="ISO timestamp of when the session was created")
    turn_count: int = Field(..., ge=0, description="Number of conversation turns")
    user_id: str | None = Field(default=None, description="User ID for multi-user tracking")
    agent_id: str | None = Field(default=None, description="Agent ID associated with the session")
    cwd_id: str | None = Field(default=None, description="File storage directory ID")
    permission_folders: list[str] | None = Field(default=None, description="Allowed write directories")
    client_type: str | None = Field(default=None, description="Client type (e.g. web, whatsapp, cli)")


class ErrorResponse(BaseModel):
    """Response model for error responses."""

    error: str = Field(..., description="Error type or category")
    detail: str | None = Field(default=None, description="Detailed error message")


class CloseSessionResponse(BaseModel):
    """Response model for closing a session."""

    status: str = Field(..., description="Status confirmation")


class DeleteSessionResponse(BaseModel):
    """Response model for deleting a session."""

    status: str = Field(..., description="Status confirmation")


class SessionHistoryResponse(BaseModel):
    """Response model for session history."""

    session_id: str = Field(..., description="Unique identifier for the session")
    messages: list = Field(default_factory=list, description="Conversation history messages")
    turn_count: int = Field(default=0, ge=0, description="Number of conversation turns")
    first_message: str | None = Field(default=None, description="The first message sent")


class SearchResultResponse(BaseModel):
    """Response model for a single search result."""

    session_id: str = Field(..., description="Unique identifier for the session")
    name: str | None = Field(default=None, description="Custom name for the session")
    first_message: str | None = Field(default=None, description="The first message sent")
    created_at: str = Field(..., description="ISO timestamp of session creation")
    turn_count: int = Field(..., ge=0, description="Number of conversation turns")
    agent_id: str | None = Field(default=None, description="Agent ID associated with the session")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0-1)")
    match_count: int = Field(..., ge=0, description="Number of query matches found")
    snippet: str | None = Field(default=None, description="Text snippet showing match context")


class SearchResponse(BaseModel):
    """Response model for search results."""

    results: list[SearchResultResponse] = Field(default_factory=list, description="Matching search results")
    total_count: int = Field(..., ge=0, description="Total number of results found")
    query: str = Field(..., description="The search query string")


class FileMetadata(BaseModel):
    """Response model for file metadata."""

    model_config = dict(arbitrary_types_allowed=True)

    safe_name: str = Field(..., description="Sanitized filename (used for storage)")
    original_name: str = Field(..., description="Original filename from upload")
    file_type: Literal["input", "output"] = Field(..., description="Type of file")
    size_bytes: int = Field(..., ge=0, description="File size in bytes")
    content_type: str = Field(..., description="MIME type of the file")
    created_at: str = Field(..., description="ISO timestamp when file was created")
    session_id: str = Field(..., description="Session ID file belongs to")

    def __str__(self) -> str:
        return f"FileMetadata(safe_name=\"{self.safe_name}\", original_name=\"{self.original_name}\")"


class FileUploadResponse(BaseModel):
    """Response model for file upload."""

    success: bool = Field(..., description="Whether the upload was successful")
    file: FileMetadata | None = Field(default=None, description="File metadata if successful")
    error: str | None = Field(default=None, description="Error message if failed")
    total_files: int = Field(..., ge=0, description="Total files in session after upload")
    total_size_bytes: int = Field(..., ge=0, description="Total size of all files in bytes")


class FileListResponse(BaseModel):
    """Response model for file list."""

    session_id: str = Field(..., description="Session ID files belong to")
    files: list[FileMetadata] = Field(default_factory=list, description="File metadata objects")
    total_files: int = Field(..., ge=0, description="Total number of files")
    total_size_bytes: int = Field(..., ge=0, description="Total size of all files in bytes")


class FileDeleteResponse(BaseModel):
    """Response model for file deletion."""

    success: bool = Field(..., description="Whether the deletion was successful")
    error: str | None = Field(default=None, description="Error message if failed")
    remaining_files: int = Field(..., ge=0, description="Files remaining after deletion")
