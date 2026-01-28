"""Conversation management endpoints with SSE streaming."""
import json
import logging
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from api.models.requests import SendMessageRequest, CreateConversationRequest
from api.dependencies import SessionManagerDep
from api.dependencies.auth import get_current_user
from api.models.user_auth import UserTokenPayload
from api.constants import EventType
from api.services.message_utils import convert_messages_to_sse
from api.services.history_tracker import HistoryTracker
from agent.core.storage import get_user_history_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("")
async def create_conversation(
    request: CreateConversationRequest,
    manager: SessionManagerDep,
    user: UserTokenPayload = Depends(get_current_user)
):
    """Create a new conversation and stream the response via SSE.

    This endpoint creates a new session (or uses existing one) and sends
    the initial message, streaming back the response.

    Args:
        request: The conversation request with content and optional session info.
        manager: SessionManager dependency injection.

    Returns:
        EventSourceResponse that streams conversation events.

    Example:
        POST /api/v1/conversations
        {"content": "Hello, how can you help me?"}

        Response streams events:
        - event: session_id
        - event: text_delta (multiple)
        - event: tool_use (if tools are used)
        - event: done
    """
    # Use provided session_id or generate a new one
    session_id = request.session_id or str(uuid.uuid4())

    return EventSourceResponse(
        _stream_conversation_events(session_id, request.content, manager, request.agent_id, user.username),
        media_type="text/event-stream"
    )


async def _stream_conversation_events(
    session_id: str,
    content: str,
    manager,
    agent_id: str | None = None,
    username: str | None = None
) -> AsyncIterator[dict]:
    """Async generator that streams conversation events as SSE.

    Args:
        session_id: The session identifier (pending ID or SDK session ID).
        content: The message content to send.
        manager: SessionManager instance.
        agent_id: Optional agent ID to use for new sessions.

    Yields:
        SSE event dictionaries with 'event' and 'data' keys.
    """
    session, resolved_id, found_in_cache = await manager.get_or_create_conversation_session(
        session_id, agent_id
    )

    # Initialize history tracker for this session
    tracker = HistoryTracker(
        session_id=resolved_id,
        history=get_user_history_storage(username) if username else None
    )

    # Emit session_id event immediately at the start
    yield {
        "event": EventType.SESSION_ID,
        "data": json.dumps({
            "session_id": resolved_id,
            "found_in_cache": found_in_cache
        })
    }

    # Track pending_id for SDK session registration
    pending_id = resolved_id

    # Save user message to history
    tracker.save_user_message(content)

    try:
        async for msg in session.send_query(content):
            # Convert message to SSE format (handles UserMessage with multiple tool_results)
            sse_events = convert_messages_to_sse(msg)

            for sse_event in sse_events:
                event_type = sse_event.get("event")

                # Parse the data to save to history
                try:
                    data = json.loads(sse_event.get("data", "{}"))
                except json.JSONDecodeError:
                    data = {}

                # Handle SDK session_id - store on session, register mapping, and emit
                if event_type == EventType.SESSION_ID and "session_id" in data:
                    sdk_sid = data["session_id"]
                    session.sdk_session_id = sdk_sid  # Store for multi-turn context
                    manager.register_sdk_session_id(pending_id, sdk_sid)
                    yield {
                        "event": "sdk_session_id",
                        "data": json.dumps({"sdk_session_id": sdk_sid})
                    }
                    continue  # Don't yield the original session_id event

                # Process event through history tracker
                tracker.process_event(event_type, data)

                yield sse_event

    except Exception as e:
        logger.error(f"Error streaming conversation for session {resolved_id}: {e}", exc_info=True)

        # Save any accumulated text before error
        if tracker.has_accumulated_text():
            tracker.finalize_assistant_response(metadata={"error": str(e)})

        # Yield error event to client
        yield {
            "event": EventType.ERROR,
            "data": json.dumps({"error": str(e), "type": type(e).__name__})
        }


@router.post("/{session_id}/stream")
async def stream_conversation(
    session_id: str,
    request: SendMessageRequest,
    manager: SessionManagerDep,
    user: UserTokenPayload = Depends(get_current_user)
):
    """Send a message and stream the response via Server-Sent Events.

    Args:
        session_id: The session identifier.
        request: The message request with content.
        manager: SessionManager dependency injection.
        user: Authenticated user from JWT token.

    Returns:
        EventSourceResponse that streams conversation events.

    Example:
        POST /api/v1/conversations/abc123/stream
        {"content": "What is 2 + 2?"}

        Response streams events:
        - event: session_id
        - event: text_delta (multiple)
        - event: tool_use (if tools are used)
        - event: done
    """
    return EventSourceResponse(
        _stream_conversation_events(session_id, request.content, manager, username=user.username),
        media_type="text/event-stream"
    )


@router.post("/{session_id}/interrupt")
async def interrupt_conversation(session_id: str):
    """Interrupt the current task in a conversation.

    Args:
        session_id: The session identifier.

    Returns:
        Status confirmation.

    Note:
        This is a placeholder for future interrupt functionality.
    """
    # TODO: Implement actual interrupt logic
    # This would involve calling session.client.interrupt() or similar

    return {"status": "interrupted", "session_id": session_id}
