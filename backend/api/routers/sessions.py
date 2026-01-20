"""Session management endpoints.

Provides REST API for creating, closing, deleting, and listing sessions.
Integrates with SessionManager service for business logic.
"""
from fastapi import APIRouter, HTTPException, status

from api.models.requests import CreateSessionRequest
from api.models.responses import SessionInfo
from api.dependencies import SessionManagerDep

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
