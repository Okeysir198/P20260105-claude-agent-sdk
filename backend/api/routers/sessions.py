"""Session management endpoints."""

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from claude_agent_sdk import ClaudeSDKClient
from agent.core.agent_options import create_enhanced_options
from agent import PROJECT_ROOT
from api.core.errors import handle_service_errors, raise_not_found
from api.dependencies import get_session_manager
from api.services.history_storage import get_history_storage
from api.services.session_manager import SessionManager


router = APIRouter()


# Path utilities
def get_claude_projects_dir() -> Path:
    """Get the Claude Code projects directory."""
    return Path.home() / ".claude" / "projects"


def get_project_session_dir() -> Path:
    """Get the session directory for current project."""
    project_root = PROJECT_ROOT.parent
    project_path = str(project_root.resolve())
    project_name = project_path.replace("/", "-")
    return get_claude_projects_dir() / project_name


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


class ResumeSessionRequest(BaseModel):
    """Request model for resuming a session."""
    current_session_id: str | None = None


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


class HistoryMessage(BaseModel):
    """A message in the conversation history."""
    id: str
    role: str
    content: str
    tool_use: list[dict[str, Any]] | None = None
    tool_results: list[dict[str, Any]] | None = None
    timestamp: str | None = None


class SessionHistoryResponse(BaseModel):
    """Response model for session history."""
    session_id: str
    messages: list[HistoryMessage]
    total_messages: int


# History parsing helpers
def parse_user_content(content: Any) -> str:
    """Extract text content from user message content field."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            block.get("text", "")
            for block in content
            if block.get("type") == "text"
        )
    return ""


def parse_assistant_content(content_blocks: list[dict]) -> tuple[str, list[dict]]:
    """Parse assistant message content blocks into text and tool uses."""
    text_parts = []
    tool_uses = []

    for block in content_blocks:
        block_type = block.get("type")
        if block_type == "text":
            text_parts.append(block.get("text", ""))
        elif block_type == "tool_use":
            tool_uses.append({
                "id": block.get("id"),
                "name": block.get("name"),
                "input": block.get("input", {})
            })

    return "".join(text_parts), tool_uses


def parse_jsonl_history(session_file: Path) -> list[HistoryMessage]:
    """Parse Claude Code JSONL session file into HistoryMessage list."""
    messages: list[HistoryMessage] = []

    with open(session_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type")
            message_data = data.get("message", {})
            content = message_data.get("content", "")

            if msg_type == "user":
                messages.append(HistoryMessage(
                    id=data.get("uuid", f"user-{len(messages)}"),
                    role="user",
                    content=parse_user_content(content),
                    timestamp=data.get("timestamp")
                ))

            elif msg_type == "assistant":
                text_content, tool_uses = parse_assistant_content(
                    content if isinstance(content, list) else []
                )
                messages.append(HistoryMessage(
                    id=data.get("uuid", f"assistant-{len(messages)}"),
                    role="assistant",
                    content=text_content,
                    tool_use=tool_uses if tool_uses else None,
                    timestamp=data.get("timestamp")
                ))

    return messages


def build_history_message(msg: dict, index: int) -> HistoryMessage:
    """Build a HistoryMessage from stored message dict."""
    return HistoryMessage(
        id=msg.get("id", f"{msg['role']}-{index}"),
        role=msg["role"],
        content=msg["content"],
        tool_use=msg.get("tool_use"),
        tool_results=msg.get("tool_results"),
        timestamp=msg.get("timestamp")
    )


# Endpoints
@router.post("", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest | None = None,
    session_manager: SessionManager = Depends(get_session_manager)
) -> CreateSessionResponse:
    """Create a new session without sending a message."""
    agent_id = request.agent_id if request else None

    options = create_enhanced_options(resume_session_id=None, agent_id=agent_id)
    client = ClaudeSDKClient(options)
    await client.connect()

    temp_id = f"pending-{id(client)}"
    await session_manager.register_session(temp_id, client, None)

    return CreateSessionResponse(session_id=temp_id, status="connected")


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    session_manager: SessionManager = Depends(get_session_manager)
) -> SessionListResponse:
    """List all active and historical sessions.

    Returns sessions with history_sessions as the authoritative ordered list
    (newest first, excluding pending-* sessions). active_sessions indicates
    which have live connections.
    """
    active_session_ids = set(session_manager.get_session_ids())
    # History is authoritative for order (newest first), filter out pending
    history_sessions = [
        sid for sid in session_manager.get_session_history()
        if not sid.startswith("pending-")
    ]
    # Active sessions that aren't in history yet (e.g., pending)
    active_only = [
        sid for sid in active_session_ids
        if sid not in history_sessions and not sid.startswith("pending-")
    ]

    return SessionListResponse(
        active_sessions=list(active_session_ids),
        history_sessions=history_sessions,
        total_active=len(active_session_ids),
        total_history=len(history_sessions)
    )


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session_info(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
) -> SessionInfo:
    """Get information about a specific session."""
    client = await session_manager.get_session(session_id)
    is_active = client is not None

    if not is_active:
        history = session_manager.get_session_history()
        if session_id not in history:
            raise_not_found(f"Session {session_id} not found")

    return SessionInfo(session_id=session_id, is_active=is_active)


@router.post("/resume", response_model=ResumeSessionResponse)
@handle_service_errors("resume session")
async def resume_session(
    request: ResumeSessionRequest | None = None,
    session_manager: SessionManager = Depends(get_session_manager)
) -> ResumeSessionResponse:
    """Resume a session.

    If current_session_id is provided, finds and resumes the previous session.
    Otherwise resumes the most recent session from history.
    """
    current_session_id = request.current_session_id if request else None

    # Get session history (newest first)
    history = session_manager.get_session_history()
    valid_sessions = [s for s in history if not s.startswith("pending-")]

    if not valid_sessions:
        raise ValueError("No sessions available to resume")

    # Find session to resume
    resume_id = None
    if current_session_id:
        # Find the session before current one
        try:
            idx = valid_sessions.index(current_session_id)
            if idx + 1 < len(valid_sessions):
                resume_id = valid_sessions[idx + 1]
        except ValueError:
            pass  # Current session not in history

    # Fallback to most recent session (that isn't the current one)
    if not resume_id:
        for sid in valid_sessions:
            if sid != current_session_id:
                resume_id = sid
                break

    if not resume_id:
        raise ValueError("No previous session to resume")

    await session_manager.resume_session(resume_id)
    return ResumeSessionResponse(
        session_id=resume_id,
        message="Session resumed successfully"
    )


@router.post("/{session_id}/resume", response_model=ResumeSessionResponse)
@handle_service_errors("resume session")
async def resume_specific_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
) -> ResumeSessionResponse:
    """Resume a specific session by ID."""
    await session_manager.resume_session(session_id)
    return ResumeSessionResponse(
        session_id=session_id,
        message="Session resumed successfully"
    )


class PreviousSessionResponse(BaseModel):
    """Response model for previous session lookup."""
    previous_session_id: str | None
    current_session_id: str


@router.get("/{session_id}/previous", response_model=PreviousSessionResponse)
async def get_previous_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
) -> PreviousSessionResponse:
    """Get the session that was active before the given session.

    Looks up the session order in storage and returns the one
    immediately before the current session.
    """
    history = session_manager.get_session_history()
    # Filter out pending sessions
    valid_sessions = [s for s in history if not s.startswith("pending-")]

    previous_id = None
    try:
        idx = valid_sessions.index(session_id)
        # Previous session is the next one in the list (history is newest first)
        if idx + 1 < len(valid_sessions):
            previous_id = valid_sessions[idx + 1]
    except ValueError:
        # Session not in history, return first session as fallback
        if valid_sessions:
            previous_id = valid_sessions[0] if valid_sessions[0] != session_id else None

    return PreviousSessionResponse(
        previous_session_id=previous_id,
        current_session_id=session_id
    )


@router.post("/{session_id}/close", response_model=DeleteSessionResponse)
async def close_session_endpoint(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
) -> DeleteSessionResponse:
    """Close a session's active connection (keeps in history)."""
    await session_manager.close_session(session_id)
    return DeleteSessionResponse(
        session_id=session_id,
        message="Session closed successfully"
    )


@router.delete("/{session_id}", response_model=DeleteSessionResponse)
async def delete_session_endpoint(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
) -> DeleteSessionResponse:
    """Delete a session from both memory and history."""
    success = await session_manager.delete_session(session_id)
    if not success:
        raise_not_found(f"Session {session_id} not found")

    return DeleteSessionResponse(
        session_id=session_id,
        message="Session deleted successfully"
    )


@router.get("/{session_id}/history", response_model=SessionHistoryResponse)
@handle_service_errors("read session history")
async def get_session_history(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
) -> SessionHistoryResponse:
    """Get conversation history for a session.

    Checks local history storage first, then falls back to Claude Code JSONL files.
    """
    # Try local history storage first
    history_storage = get_history_storage()
    if history_storage.has_history(session_id):
        stored_messages = history_storage.get_history(session_id)
        messages = [
            build_history_message(msg, i)
            for i, msg in enumerate(stored_messages)
        ]
        return SessionHistoryResponse(
            session_id=session_id,
            messages=messages,
            total_messages=len(messages)
        )

    # Fall back to Claude Code JSONL file
    session_file = get_project_session_dir() / f"{session_id}.jsonl"
    if not session_file.exists():
        raise ValueError(f"History for session {session_id} not found")

    messages = parse_jsonl_history(session_file)

    return SessionHistoryResponse(
        session_id=session_id,
        messages=messages,
        total_messages=len(messages)
    )
