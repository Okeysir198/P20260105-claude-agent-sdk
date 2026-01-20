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
