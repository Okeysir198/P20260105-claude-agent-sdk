"""Session management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from claude_agent_sdk import ClaudeSDKClient
from agent.core.agent_options import create_enhanced_options
from api.services.session_manager import SessionManager
from api.dependencies import get_session_manager


router = APIRouter()


# Request/Response Models
class CreateSessionRequest(BaseModel):
    """Request model for creating a session."""
    agent_id: str | None = None


class SessionInfo(BaseModel):
    """Session information model."""
    session_id: str
    is_active: bool


class SessionListResponse(BaseModel):
    """Response model for listing sessions."""
    active_sessions: list[str]
    history_sessions: list[str]
    total_active: int
    total_history: int


class ResumeSessionResponse(BaseModel):
    """Response model for resuming a session."""
    session_id: str
    message: str


class DeleteSessionResponse(BaseModel):
    """Response model for deleting a session."""
    session_id: str
    message: str


class CreateSessionResponse(BaseModel):
    """Response model for creating a session."""
    session_id: str
    status: str


# Endpoints
@router.post("", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest | None = None,
    session_manager: SessionManager = Depends(get_session_manager)
) -> CreateSessionResponse:
    """Create a new session without sending a message.

    The client is initialized and ready for messages.
    Use the returned session_id with the /stream endpoint.

    Args:
        request: Optional request with agent_id selection
        session_manager: Session manager dependency

    Returns:
        Session creation response with temporary session_id
    """
    # Extract agent_id from request if provided
    agent_id = request.agent_id if request else None

    # Create and connect client
    options = create_enhanced_options(resume_session_id=None, agent_id=agent_id)
    client = ClaudeSDKClient(options)
    await client.connect()

    # Generate temporary ID (real ID comes from first message)
    temp_id = f"pending-{id(client)}"

    # Register with temporary ID
    await session_manager.register_session(temp_id, client, None)

    return CreateSessionResponse(
        session_id=temp_id,
        status="connected"
    )


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    session_manager: SessionManager = Depends(get_session_manager)
) -> SessionListResponse:
    """List all active and historical sessions.

    Args:
        session_manager: Session manager dependency

    Returns:
        List of active and historical sessions
    """
    active_sessions = session_manager.list_active_sessions()
    history_sessions = session_manager.get_session_history()

    return SessionListResponse(
        active_sessions=active_sessions,
        history_sessions=history_sessions,
        total_active=len(active_sessions),
        total_history=len(history_sessions)
    )


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session_info(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
) -> SessionInfo:
    """Get information about a specific session.

    Args:
        session_id: Session ID to query
        session_manager: Session manager dependency

    Returns:
        Session information

    Raises:
        HTTPException: If session not found
    """
    client = await session_manager.get_session(session_id)
    is_active = client is not None

    # Check if it exists in history even if not active
    if not is_active:
        history = session_manager.get_session_history()
        if session_id not in history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

    return SessionInfo(
        session_id=session_id,
        is_active=is_active
    )


@router.post("/{session_id}/resume", response_model=ResumeSessionResponse)
async def resume_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
) -> ResumeSessionResponse:
    """Resume an existing session.

    Args:
        session_id: Session ID to resume
        session_manager: Session manager dependency

    Returns:
        Resume confirmation

    Raises:
        HTTPException: If session cannot be resumed
    """
    try:
        await session_manager.resume_session(session_id)
        return ResumeSessionResponse(
            session_id=session_id,
            message="Session resumed successfully"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume session: {str(e)}"
        )


@router.delete("/{session_id}", response_model=DeleteSessionResponse)
async def delete_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
) -> DeleteSessionResponse:
    """Close and delete a session.

    Args:
        session_id: Session ID to delete
        session_manager: Session manager dependency

    Returns:
        Deletion confirmation

    Raises:
        HTTPException: If session not found
    """
    success = await session_manager.close_session(session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    return DeleteSessionResponse(
        session_id=session_id,
        message="Session closed successfully"
    )
