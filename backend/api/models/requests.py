"""Request models for FastAPI endpoints."""

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    """Request model for creating a new session.

    Attributes:
        agent_id: Optional identifier for the agent to use
        resume_session_id: Optional session ID to resume from a previous session
    """

    agent_id: str | None = Field(
        default=None,
        description="Identifier for the agent to use in this session"
    )
    resume_session_id: str | None = Field(
        default=None,
        description="Session ID to resume from a previous conversation"
    )


class SendMessageRequest(BaseModel):
    """Request model for sending a message to an agent.

    Attributes:
        content: The message content to send
    """

    content: str = Field(
        ...,
        min_length=1,
        description="The message content to send to the agent"
    )


class CreateConversationRequest(BaseModel):
    """Request model for creating a new conversation.

    Attributes:
        content: The initial message content
        session_id: Optional existing session ID to use
        agent_id: Optional agent ID to use
        resume_session_id: Optional session ID to resume from
    """

    content: str = Field(
        ...,
        min_length=1,
        description="The message content to send to the agent"
    )
    session_id: str | None = Field(
        default=None,
        description="Optional existing session ID to use"
    )
    agent_id: str | None = Field(
        default=None,
        description="Optional agent ID to use"
    )
    resume_session_id: str | None = Field(
        default=None,
        description="Optional session ID to resume from"
    )


class ResumeSessionRequest(BaseModel):
    """Request model for resuming a session.

    Attributes:
        initial_message: Optional message to send when resuming
    """

    initial_message: str | None = Field(
        default=None,
        description="Optional message to send when resuming the session"
    )


class UpdateSessionRequest(BaseModel):
    """Request model for updating session properties.

    Attributes:
        name: New custom name for the session
    """

    name: str | None = Field(
        default=None,
        description="New custom name for the session"
    )


class BatchDeleteSessionsRequest(BaseModel):
    """Request model for batch deleting sessions.

    Attributes:
        session_ids: List of session IDs to delete
    """

    session_ids: list[str] = Field(
        ...,
        description="List of session IDs to delete",
        min_length=1
    )
