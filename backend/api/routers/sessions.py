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
from api.services.search_service import SearchOptions, SessionSearchService
from api.utils.sensitive_data_filter import sanitize_event_paths, sanitize_paths

router = APIRouter(prefix="/sessions", tags=["sessions"])


async def _delete_single_session(
    session_id: str,
    username: str,
    manager: SessionManagerDep,
) -> None:
    """Delete a single session from cache and storage.

    Closes the in-memory cache entry (if present), then removes
    session metadata, history, and uploaded files from disk.
    """
    try:
        await manager.close_session(session_id)
    except Exception:
        pass

    session_storage = get_user_session_storage(username)
    history_storage = get_user_history_storage(username)

    # Look up cwd_id BEFORE deleting metadata so we delete the correct files dir
    session_data = session_storage.get_session(session_id)
    files_dir_id = session_data.cwd_id if session_data and session_data.cwd_id else session_id

    session_storage.delete_session(session_id)
    history_storage.delete_history(session_id)
    delete_session_files(username=username, session_id=files_dir_id)


def _extract_first_message(messages: list[dict]) -> str | None:
    """Extract the first user message text from a message list.

    Handles both string content and multi-part content (text + images).
    """
    if not messages or messages[0].get("role") != "user":
        return None

    content = messages[0].get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list) and content:
        first_block = content[0]
        if isinstance(first_block, dict):
            return first_block.get("text", "")
        return str(first_block)
    return None


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
    """Create a new session or resume an existing one."""
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
    """Close a session while keeping it in history."""
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
    """Delete a session."""
    await _delete_single_session(id, user.username, manager)
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
    """Delete multiple sessions at once."""
    for session_id in request.session_ids:
        await _delete_single_session(session_id, user.username, manager)
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
    """Update a session's properties (e.g. name, permission folders)."""
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
        cwd_id=session.cwd_id,
        permission_folders=session.permission_folders,
        client_type=session.client_type,
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
    """List all sessions for the current user, ordered by recency."""
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
            cwd_id=s.cwd_id,
            permission_folders=s.permission_folders,
            client_type=s.client_type,
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
    """Resume the previous session by its ID."""
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

    Returns empty response (not 404) if session does not exist,
    allowing the frontend to handle stale session IDs gracefully.
    """
    storage = get_user_session_storage(user.username)
    history_storage = get_user_history_storage(user.username)

    # Get messages from local history storage and sanitize paths
    messages = history_storage.get_messages_dict(id)
    for m in messages:
        sanitize_event_paths(m)

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

    # Session not found in storage - return messages if any exist.
    # This allows frontend to handle stale session IDs gracefully.
    first_message = _extract_first_message(messages)
    user_turn_count = sum(1 for m in messages if m.get("role") == "user")

    return SessionHistoryResponse(
        session_id=id,
        messages=messages,
        turn_count=user_turn_count,
        first_message=first_message,
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
    """Resume a specific session by ID."""
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
    """Search sessions by query text with relevance scoring."""
    if not query or not query.strip():
        return SearchResponse(results=[], total_count=0, query=query)

    max_results = min(max_results, 100)

    search_service = SessionSearchService(options=SearchOptions(max_results=max_results))
    results = search_service.search_sessions(username=user.username, query=query)

    # Convert to response models with sanitized paths
    search_results = [
        SearchResultResponse(
            session_id=r.session_id,
            name=r.name,
            first_message=sanitize_paths(r.first_message) if r.first_message else r.first_message,
            created_at=r.created_at,
            turn_count=r.turn_count,
            agent_id=r.agent_id,
            relevance_score=r.relevance_score,
            match_count=r.match_count,
            snippet=sanitize_paths(r.snippet) if r.snippet else r.snippet,
        )
        for r in results
    ]

    return SearchResponse(
        results=search_results,
        total_count=len(search_results),
        query=query
    )
