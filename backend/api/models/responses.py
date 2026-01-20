"""Response models for FastAPI endpoints."""

from pydantic import BaseModel, Field


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
        first_message: The first message sent in the session
        created_at: ISO timestamp of when the session was created
        turn_count: Number of conversation turns in the session
        user_id: Optional user ID for multi-user tracking
    """

    session_id: str = Field(
        ...,
        description="Unique identifier for the session"
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
