"""Session management endpoints."""

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from claude_agent_sdk import ClaudeSDKClient
from agent.core.agent_options import create_enhanced_options
from api.services.session_manager import SessionManager
from api.dependencies import get_session_manager
from agent import PROJECT_ROOT


def get_claude_projects_dir() -> Path:
    """Get the Claude Code projects directory."""
    return Path.home() / ".claude" / "projects"


def get_project_session_dir() -> Path:
    """Get the session directory for current project.

    Claude CLI stores history based on the project root path,
    not the current working directory. PROJECT_ROOT points to
    backend/, so we use its parent to get the main project root.
    """
    # PROJECT_ROOT is backend/, we need the main project root (parent)
    project_root = PROJECT_ROOT.parent
    project_path = str(project_root.resolve())
    # Claude uses path with dashes instead of slashes (keeps leading dash)
    project_name = project_path.replace("/", "-")
    return get_claude_projects_dir() / project_name


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


class HistoryMessage(BaseModel):
    """A message in the conversation history."""
    id: str
    role: str  # "user" or "assistant"
    content: str
    tool_use: list[dict[str, Any]] | None = None
    tool_results: list[dict[str, Any]] | None = None
    timestamp: str | None = None


class SessionHistoryResponse(BaseModel):
    """Response model for session history."""
    session_id: str
    messages: list[HistoryMessage]
    total_messages: int


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


@router.get("/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
) -> SessionHistoryResponse:
    """Get conversation history for a session.

    Loads messages from the Claude Code JSONL file.

    Args:
        session_id: Session ID to get history for
        session_manager: Session manager dependency

    Returns:
        Session history with all messages

    Raises:
        HTTPException: If session history not found
    """
    # Find the session JSONL file
    session_dir = get_project_session_dir()
    session_file = session_dir / f"{session_id}.jsonl"

    if not session_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"History for session {session_id} not found"
        )

    messages: list[HistoryMessage] = []

    try:
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

                # Handle user messages
                if msg_type == "user":
                    message_data = data.get("message", {})
                    content = message_data.get("content", "")
                    if isinstance(content, list):
                        # Extract text from content blocks
                        content = " ".join(
                            block.get("text", "")
                            for block in content
                            if block.get("type") == "text"
                        )

                    messages.append(HistoryMessage(
                        id=data.get("uuid", f"user-{len(messages)}"),
                        role="user",
                        content=content,
                        timestamp=data.get("timestamp")
                    ))

                # Handle assistant messages
                elif msg_type == "assistant":
                    message_data = data.get("message", {})
                    content_blocks = message_data.get("content", [])

                    # Extract text content
                    text_content = ""
                    tool_uses = []

                    for block in content_blocks:
                        if block.get("type") == "text":
                            text_content += block.get("text", "")
                        elif block.get("type") == "tool_use":
                            tool_uses.append({
                                "id": block.get("id"),
                                "name": block.get("name"),
                                "input": block.get("input", {})
                            })

                    messages.append(HistoryMessage(
                        id=data.get("uuid", f"assistant-{len(messages)}"),
                        role="assistant",
                        content=text_content,
                        tool_use=tool_uses if tool_uses else None,
                        timestamp=data.get("timestamp")
                    ))

                # Handle tool results (from user messages with tool_result content)
                elif msg_type == "user" and data.get("message", {}).get("content"):
                    content = data.get("message", {}).get("content", [])
                    if isinstance(content, list):
                        tool_results = []
                        for block in content:
                            if block.get("type") == "tool_result":
                                tool_results.append({
                                    "tool_use_id": block.get("tool_use_id"),
                                    "content": block.get("content"),
                                    "is_error": block.get("is_error", False)
                                })
                        if tool_results and messages:
                            # Attach tool results to previous assistant message
                            for msg in reversed(messages):
                                if msg.role == "assistant" and msg.tool_use:
                                    msg.tool_results = tool_results
                                    break

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read session history: {str(e)}"
        )

    return SessionHistoryResponse(
        session_id=session_id,
        messages=messages,
        total_messages=len(messages)
    )
