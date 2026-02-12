"""Session management endpoints.

Provides REST API for creating, closing, deleting, and listing sessions.
Integrates with SessionManager service for business logic.
Uses per-user storage for data isolation between authenticated users.
"""
from fastapi import APIRouter, Depends, status

from agent.core.file_storage import delete_session_files
from agent.core.storage import get_user_history_storage, get_user_session_storage
from api.core.errors import InvalidRequestError
from api.dependencies import SessionManagerDep
from api.dependencies.auth import get_current_user
from api.models.requests import (
    BatchDeleteSessionsRequest,
    CreateSessionRequest,
    ResumeSessionRequest,
    UpdateSessionRequest,
)
from api.models.responses import (
    CloseSessionResponse,
    DeleteSessionResponse,
    SearchResponse,
    SearchResultResponse,
    SessionHistoryResponse,
    SessionInfo,
    SessionResponse,
)
from api.models.user_auth import UserTokenPayload

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new session",
    description="Create a new conversation session or resume an existing one"
)
async def create_session(
    request: CreateSessionRequest,
    manager: SessionManagerDep,
    user: UserTokenPayload = Depends(get_current_user)
) -> SessionResponse:
    """Create a new session.

    Args:
        request: Session creation request with optional agent_id and resume_session_id
        manager: SessionManager dependency injection
        user: Authenticated user from token

    Returns:
        SessionResponse with session_id and status
    """
    session_id = await manager.create_session(
        agent_id=request.agent_id,
        resume_session_id=request.resume_session_id
    )
    return SessionResponse(
        session_id=session_id,
        status="ready",
        resumed=request.resume_session_id is not None
    )


@router.post(
    "/{id}/close",
    response_model=CloseSessionResponse,
    summary="Close a session",
    description="Close a session while keeping it in history"
)
async def close_session(
    id: str,
    manager: SessionManagerDep,
    user: UserTokenPayload = Depends(get_current_user)
) -> CloseSessionResponse:
    """Close a session.

    Args:
        id: Session ID to close
        manager: SessionManager dependency injection
        user: Authenticated user from token

    Returns:
        CloseSessionResponse with status="closed"
    """
    await manager.close_session(id)
    return CloseSessionResponse(status="closed")


@router.delete(
    "/{id}",
    response_model=DeleteSessionResponse,
    summary="Delete a session",
    description="Delete a session from storage"
)
async def delete_session(
    id: str,
    manager: SessionManagerDep,
    user: UserTokenPayload = Depends(get_current_user)
) -> DeleteSessionResponse:
    """Delete a session.

    Args:
        id: Session ID to delete
        manager: SessionManager dependency injection
        user: Authenticated user from token

    Returns:
        DeleteSessionResponse with status="deleted"
    """
    # Try to delete from manager (in-memory cache)
    # If not in cache, that's OK - just delete from storage
    try:
        await manager.delete_session(id)
    except Exception as e:
        # Session not in cache, but might still exist in storage
        # This is expected for sessions loaded from disk that were never in cache
        pass

    # Use user-specific storage for data isolation
    session_storage = get_user_session_storage(user.username)
    history_storage = get_user_history_storage(user.username)

    # Look up cwd_id BEFORE deleting metadata, so we delete the correct files dir
    session_data = session_storage.get_session(id)
    files_dir_id = session_data.cwd_id if session_data and session_data.cwd_id else id

    session_storage.delete_session(id)
    history_storage.delete_history(id)
    delete_session_files(username=user.username, session_id=files_dir_id)

    return DeleteSessionResponse(status="deleted")


@router.post(
    "/batch-delete",
    response_model=DeleteSessionResponse,
    summary="Delete multiple sessions",
    description="Delete multiple sessions at once"
)
async def batch_delete_sessions(
    request: BatchDeleteSessionsRequest,
    manager: SessionManagerDep,
    user: UserTokenPayload = Depends(get_current_user)
) -> DeleteSessionResponse:
    """Delete multiple sessions at once.

    Args:
        request: Batch delete request with session IDs
        manager: SessionManager dependency injection
        user: Authenticated user from token

    Returns:
        DeleteSessionResponse with status="deleted"
    """
    session_storage = get_user_session_storage(user.username)
    history_storage = get_user_history_storage(user.username)

    for session_id in request.session_ids:
        # Try to delete from manager (in-memory cache)
        try:
            await manager.delete_session(session_id)
        except Exception as e:
            # Session not in cache, but might still exist in storage
            # This is expected for sessions loaded from disk that were never in cache
            pass

        # Look up cwd_id BEFORE deleting metadata
        session_data = session_storage.get_session(session_id)
        files_dir_id = session_data.cwd_id if session_data and session_data.cwd_id else session_id

        # Delete from user storage
        session_storage.delete_session(session_id)
        history_storage.delete_history(session_id)
        delete_session_files(username=user.username, session_id=files_dir_id)

    return DeleteSessionResponse(status="deleted")


@router.patch(
    "/{id}",
    response_model=SessionInfo,
    summary="Update a session",
    description="Update session properties like name"
)
async def update_session(
    id: str,
    request: UpdateSessionRequest,
    user: UserTokenPayload = Depends(get_current_user)
) -> SessionInfo:
    """Update a session's properties.

    Args:
        id: Session ID to update
        request: Update request with new properties
        user: Authenticated user from token

    Returns:
        Updated SessionInfo
    """
    session_storage = get_user_session_storage(user.username)

    # Update the session
    updated = session_storage.update_session(
        session_id=id,
        name=request.name,
        permission_folders=request.permission_folders,
    )

    if not updated:
        raise InvalidRequestError(message=f"Session {id} not found")

    # Return updated session info
    session = session_storage.get_session(id)
    if not session:
        raise InvalidRequestError(message=f"Session {id} not found")

    return SessionInfo(
        session_id=session.session_id,
        name=session.name,
        first_message=session.first_message,
        created_at=session.created_at,
        turn_count=session.turn_count,
        cwd_id=getattr(session, 'cwd_id', None),
        permission_folders=getattr(session, 'permission_folders', None),
    )


@router.get(
    "",
    response_model=list[SessionInfo],
    summary="List all sessions",
    description="List all sessions ordered by recency (newest first)"
)
async def list_sessions(
    manager: SessionManagerDep,
    user: UserTokenPayload = Depends(get_current_user)
) -> list[SessionInfo]:
    """List all sessions for the current user.

    Args:
        manager: SessionManager dependency injection
        user: Authenticated user from token

    Returns:
        List of SessionInfo objects with session details
    """
    # Get user-specific storage for data isolation
    session_storage = get_user_session_storage(user.username)
    sessions = session_storage.load_sessions()

    return [
        SessionInfo(
            session_id=s.session_id,
            name=s.name,
            first_message=s.first_message,
            created_at=s.created_at,
            turn_count=s.turn_count,
            agent_id=s.agent_id,
            cwd_id=getattr(s, 'cwd_id', None),
            permission_folders=getattr(s, 'permission_folders', None),
        )
        for s in sessions
    ]


@router.post(
    "/resume",
    response_model=SessionResponse,
    summary="Resume previous session",
    description="Resume the previous session before the current one"
)
async def resume_previous_session(
    request: CreateSessionRequest,
    manager: SessionManagerDep,
    user: UserTokenPayload = Depends(get_current_user)
) -> SessionResponse:
    """Resume the previous session.

    Args:
        request: Optional request with resume_session_id
        manager: SessionManager dependency injection
        user: Authenticated user from token

    Returns:
        SessionResponse with session_id and resumed=True
    """
    if not request.resume_session_id:
        raise InvalidRequestError(message="resume_session_id is required")

    session_id = await manager.create_session(
        resume_session_id=request.resume_session_id
    )
    return SessionResponse(
        session_id=session_id,
        status="ready",
        resumed=True
    )


@router.get(
    "/{id}/history",
    response_model=SessionHistoryResponse,
    summary="Get session history",
    description="Get the conversation history for a session"
)
async def get_session_history(
    id: str,
    user: UserTokenPayload = Depends(get_current_user)
) -> SessionHistoryResponse:
    """Get conversation history for a session.

    Returns locally stored conversation messages from data/{username}/history/{session_id}.jsonl

    Args:
        id: Session ID to get history for
        user: Authenticated user from token

    Returns:
        SessionHistoryResponse with session info and messages array
    """
    # Use user-specific storage for data isolation
    storage = get_user_session_storage(user.username)
    history_storage = get_user_history_storage(user.username)

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
    response_model=SessionResponse,
    summary="Resume a specific session",
    description="Resume a session by its ID"
)
async def resume_session_by_id(
    id: str,
    manager: SessionManagerDep,
    user: UserTokenPayload = Depends(get_current_user),
    request: ResumeSessionRequest | None = None
) -> SessionResponse:
    """Resume a specific session by ID.

    Args:
        id: Session ID to resume
        manager: SessionManager dependency injection
        user: Authenticated user from token
        request: Optional request with initial_message

    Returns:
        SessionResponse with session_id and resumed=True
    """
    session_id = await manager.create_session(
        resume_session_id=id
    )
    return SessionResponse(
        session_id=session_id,
        status="ready",
        resumed=True
    )


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Search sessions",
    description="Search sessions by query text with relevance scoring"
)
async def search_sessions(
    query: str,
    max_results: int = 20,
    user: UserTokenPayload = Depends(get_current_user)
) -> SearchResponse:
    """Search sessions by query text.

    Searches through session names, first messages, and conversation history
    to find matching sessions. Results are ranked by relevance score.

    Args:
        query: Search query string
        max_results: Maximum number of results to return (default 20, max 100)
        user: Authenticated user from token

    Returns:
        SearchResponse with ranked results and metadata
    """
    # Return empty results for empty queries
    if not query or not query.strip():
        return SearchResponse(
            results=[],
            total_count=0,
            query=query
        )

    # Limit max_results to prevent excessive responses
    max_results = min(max_results, 100)

    # Import search service
    from api.services.search_service import SessionSearchService, SearchOptions

    # Create search options
    search_options = SearchOptions(max_results=max_results)

    # Create search service and perform search
    search_service = SessionSearchService(options=search_options)

    results = search_service.search_sessions(
        username=user.username,
        query=query
    )

    # Convert to response models
    search_results = [
        SearchResultResponse(
            session_id=r.session_id,
            name=r.name,
            first_message=r.first_message,
            created_at=r.created_at,
            turn_count=r.turn_count,
            agent_id=r.agent_id,
            relevance_score=r.relevance_score,
            match_count=r.match_count,
            snippet=r.snippet
        )
        for r in results
    ]

    return SearchResponse(
        results=search_results,
        total_count=len(search_results),
        query=query
    )
