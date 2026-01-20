"""Conversation management endpoints with SSE streaming."""
import json
import logging
import uuid
from typing import AsyncIterator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from api.models.requests import SendMessageRequest, CreateConversationRequest
from api.dependencies import SessionManagerDep
from api.services.message_utils import convert_message_to_sse
from agent.core.storage import get_history_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("")
async def create_conversation(
    request: CreateConversationRequest,
    manager: SessionManagerDep
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

    logger.info(f"Creating conversation with session: {session_id}, agent_id: {request.agent_id}")

    return EventSourceResponse(
        _stream_conversation_events(session_id, request.content, manager, request.agent_id),
        media_type="text/event-stream"
    )


async def _stream_conversation_events(
    session_id: str,
    content: str,
    manager,
    agent_id: str | None = None
) -> AsyncIterator[dict]:
    """Async generator that streams conversation events as SSE.

    Args:
        session_id: The session identifier.
        content: The message content to send.
        manager: SessionManager instance.
        agent_id: Optional agent ID to use for new sessions.

    Yields:
        SSE event dictionaries with 'event' and 'data' keys.
    """
    session = await manager.get_or_create_conversation_session(session_id, agent_id)
    history = get_history_storage()

    # Emit session_id event immediately at the start
    yield {
        "event": "session_id",
        "data": json.dumps({"session_id": session_id})
    }

    # Save user message to history
    history.append_message(
        session_id=session_id,
        role="user",
        content=content
    )

    # Accumulate assistant response text
    assistant_text_parts = []

    try:
        # Connect session if not already connected
        if not session.is_connected:
            await session.connect()
            logger.info(f"Connected session: {session_id}")

        # Send query and stream response
        await session.client.query(content)

        async for msg in session.client.receive_response():
            # Convert message to SSE format
            sse_event = convert_message_to_sse(msg)

            if sse_event:
                event_type = sse_event.get("event")

                # Parse the data to save to history
                try:
                    data = json.loads(sse_event.get("data", "{}"))
                except json.JSONDecodeError:
                    data = {}

                # Accumulate text deltas for assistant message
                if event_type == "text_delta" and "text" in data:
                    assistant_text_parts.append(data["text"])

                # Save tool_use to history
                elif event_type == "tool_use":
                    history.append_message(
                        session_id=session_id,
                        role="tool_use",
                        content=json.dumps(data.get("input", {})),
                        tool_name=data.get("tool_name"),
                        tool_use_id=data.get("tool_use_id")
                    )

                # Save tool_result to history
                elif event_type == "tool_result":
                    history.append_message(
                        session_id=session_id,
                        role="tool_result",
                        content=str(data.get("content", "")),
                        tool_use_id=data.get("tool_use_id"),
                        is_error=data.get("is_error", False)
                    )

                # On done, save accumulated assistant response
                elif event_type == "done":
                    if assistant_text_parts:
                        history.append_message(
                            session_id=session_id,
                            role="assistant",
                            content="".join(assistant_text_parts)
                        )
                        assistant_text_parts = []

                yield sse_event

    except Exception as e:
        logger.error(f"Error streaming conversation for session {session_id}: {e}")

        # Save any accumulated text before error
        if assistant_text_parts:
            history.append_message(
                session_id=session_id,
                role="assistant",
                content="".join(assistant_text_parts),
                metadata={"error": str(e)}
            )

        # Yield error event to client
        yield {
            "event": "error",
            "data": json.dumps({"error": str(e), "type": type(e).__name__})
        }


@router.post("/{session_id}/stream")
async def stream_conversation(
    session_id: str,
    request: SendMessageRequest,
    manager: SessionManagerDep
):
    """Send a message and stream the response via Server-Sent Events.

    Args:
        session_id: The session identifier.
        request: The message request with content.
        manager: SessionManager dependency injection.

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
    logger.info(f"Streaming conversation for session: {session_id}")

    return EventSourceResponse(
        _stream_conversation_events(session_id, request.content, manager),
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
    logger.info(f"Interrupt requested for session: {session_id}")

    # TODO: Implement actual interrupt logic
    # This would involve calling session.client.interrupt() or similar

    return {"status": "interrupted", "session_id": session_id}
