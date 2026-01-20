"""Session management endpoints.

Provides REST API for creating, closing, deleting, and listing sessions.
Integrates with SessionManager service for business logic.
"""
from fastapi import APIRouter, HTTPException, status

from api.models.requests import CreateSessionRequest, ResumeSessionRequest
from api.models.responses import SessionInfo, SessionHistoryResponse
from api.dependencies import SessionManagerDep
from agent.core.storage import get_storage, get_history_storage

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post(
    "",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new session",
    description="Create a new conversation session or resume an existing one"
)
async def create_session(
    request: CreateSessionRequest,
    manager: SessionManagerDep
) -> dict:
    """Create a new session.

    Args:
        request: Session creation request with optional agent_id and resume_session_id
        manager: SessionManager dependency injection

    Returns:
        Dictionary with session_id and status
    """
    session_id = await manager.create_session(
        agent_id=request.agent_id,
        resume_session_id=request.resume_session_id
    )
    return {
        "session_id": session_id,
        "status": "ready",
        "resumed": request.resume_session_id is not None
    }


@router.post(
    "/{id}/close",
    response_model=dict,
    summary="Close a session",
    description="Close a session while keeping it in history"
)
async def close_session(
    id: str,
    manager: SessionManagerDep
) -> dict:
    """Close a session.

    Args:
        id: Session ID to close
        manager: SessionManager dependency injection

    Returns:
        Dictionary with status="closed"
    """
    await manager.close_session(id)
    return {"status": "closed"}


@router.delete(
    "/{id}",
    response_model=dict,
    summary="Delete a session",
    description="Delete a session from storage"
)
async def delete_session(
    id: str,
    manager: SessionManagerDep
) -> dict:
    """Delete a session.

    Args:
        id: Session ID to delete
        manager: SessionManager dependency injection

    Returns:
        Dictionary with status="deleted"
    """
    await manager.delete_session(id)

    # Also delete local history file
    history_storage = get_history_storage()
    history_storage.delete_history(id)

    return {"status": "deleted"}


@router.get(
    "",
    response_model=list[SessionInfo],
    summary="List all sessions",
    description="List all sessions ordered by recency (newest first)"
)
async def list_sessions(manager: SessionManagerDep) -> list[SessionInfo]:
    """List all sessions.

    Args:
        manager: SessionManager dependency injection

    Returns:
        List of SessionInfo objects with session details
    """
    return manager.list_sessions()


@router.post(
    "/resume",
    response_model=dict,
    summary="Resume previous session",
    description="Resume the previous session before the current one"
)
async def resume_previous_session(
    request: CreateSessionRequest,
    manager: SessionManagerDep
) -> dict:
    """Resume the previous session.

    Args:
        request: Optional request with resume_session_id
        manager: SessionManager dependency injection

    Returns:
        Dictionary with session_id and resumed=True
    """
    if not request.resume_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "resume_session_id is required"}
        )

    session_id = await manager.create_session(
        resume_session_id=request.resume_session_id
    )
    return {
        "session_id": session_id,
        "status": "ready",
        "resumed": True
    }


@router.get(
    "/{id}/history",
    response_model=SessionHistoryResponse,
    summary="Get session history",
    description="Get the conversation history for a session"
)
async def get_session_history(id: str) -> SessionHistoryResponse:
    """Get conversation history for a session.

    Returns locally stored conversation messages from data/history/{session_id}.jsonl

    Args:
        id: Session ID to get history for

    Returns:
        SessionHistoryResponse with session info and messages array
    """
    storage = get_storage()
    history_storage = get_history_storage()

    # Get messages from local history storage
    messages = history_storage.get_messages_dict(id)

    # Find session metadata
    sessions = storage.load_sessions()
    session_data = None
    for session in sessions:
        if session.session_id == id:
            session_data = session
            break

    if session_data:
        return SessionHistoryResponse(
            session_id=id,
            messages=messages,
            turn_count=session_data.turn_count,
            first_message=session_data.first_message
        )

    # Session not found in storage - return messages if any exist
    return SessionHistoryResponse(
        session_id=id,
        messages=messages,
        turn_count=len([m for m in messages if m.get("role") == "user"]),
        first_message=messages[0]["content"] if messages and messages[0].get("role") == "user" else None
    )


@router.post(
    "/{id}/resume",
    response_model=dict,
    summary="Resume a specific session",
    description="Resume a session by its ID"
)
async def resume_session_by_id(
    id: str,
    manager: SessionManagerDep,
    request: ResumeSessionRequest | None = None
) -> dict:
    """Resume a specific session by ID.

    Args:
        id: Session ID to resume
        manager: SessionManager dependency injection
        request: Optional request with initial_message

    Returns:
        Dictionary with session_id and resumed=True
    """
    session_id = await manager.create_session(
        resume_session_id=id
    )
    return {
        "session_id": session_id,
        "status": "ready",
        "resumed": True
    }
