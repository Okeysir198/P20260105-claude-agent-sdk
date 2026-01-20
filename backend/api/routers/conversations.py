"""Conversation management endpoints with SSE streaming."""
import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from api.models.requests import SendMessageRequest
from api.dependencies import SessionManagerDep
from api.services.message_utils import convert_message_to_sse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


async def _stream_conversation_events(
    session_id: str,
    content: str,
    manager
) -> AsyncIterator[dict]:
    """Async generator that streams conversation events as SSE.

    Args:
        session_id: The session identifier.
        content: The message content to send.
        manager: SessionManager instance.

    Yields:
        SSE event dictionaries with 'event' and 'data' keys.
    """
    session = await manager.get_or_create_conversation_session(session_id)

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
                yield sse_event

    except Exception as e:
        logger.error(f"Error streaming conversation for session {session_id}: {e}")
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
