"""Conversation endpoints for message handling."""

import json
from typing import Any, AsyncIterator, Callable

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from api.core.errors import handle_service_errors
from api.dependencies import get_conversation_service
from api.services.conversation_service import ConversationService


router = APIRouter(tags=["conversations"])


# Request/Response Models
class CreateConversationRequest(BaseModel):
    """Request model for creating a conversation with first message."""
    content: str
    resume_session_id: str | None = None
    agent_id: str | None = None
    pending_session_id: str | None = None  # Pending session ID from POST /api/v1/sessions
    user_id: str | None = None  # Optional user ID for multi-user tracking


class SendMessageRequest(BaseModel):
    """Request model for sending a message."""
    content: str
    user_id: str | None = None  # Optional user ID for multi-user tracking


class MessageResponse(BaseModel):
    """Response model for message sending."""
    session_id: str
    response: str
    tool_uses: list[dict[str, Any]]
    turn_count: int
    messages: list[dict[str, Any]]


class InterruptResponse(BaseModel):
    """Response model for interrupt."""
    session_id: str
    message: str


async def create_sse_generator(
    stream_func: Callable[[], AsyncIterator[dict[str, Any]]],
    error_prefix: str = "Streaming failed"
) -> AsyncIterator[dict[str, str]]:
    """Create an SSE event generator from a stream function.

    Args:
        stream_func: Async generator function that yields event dictionaries
        error_prefix: Prefix for error messages

    Yields:
        SSE-formatted event dictionaries with event type and JSON data
    """
    # Create the stream iterator once to ensure we can consume it fully
    stream_iterator = stream_func()

    try:
        async for event_data in stream_iterator:
            yield {
                "event": event_data.get("event", "message"),
                "data": json.dumps(event_data.get("data", {}))
            }
    except ValueError as e:
        yield {"event": "error", "data": json.dumps({"error": str(e)})}
    except Exception as e:
        yield {"event": "error", "data": json.dumps({"error": f"{error_prefix}: {str(e)}"})}
    finally:
        # IMPORTANT: Consume the entire stream even if client disconnects
        # This ensures the Claude SDK client completes its response cycle properly
        try:
            async for _ in stream_iterator:
                pass  # Consume remaining events
        except GeneratorExit:
            # Stream generator was closed, this is expected
            pass
        except Exception as e:
            # Log any errors during cleanup but don't raise
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error during stream cleanup: {e}")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: CreateConversationRequest,
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> EventSourceResponse:
    """Create a new conversation and send the first message.

    SSE Events:
        - session_id: Real session ID from SDK
        - text_delta: Streaming text chunks
        - tool_use: Tool invocation
        - tool_result: Tool result
        - done: Conversation complete
    """
    def stream_func() -> AsyncIterator[dict[str, Any]]:
        return conversation_service.create_and_stream(
            request.content,
            request.resume_session_id,
            request.agent_id,
            request.user_id,
        )

    return EventSourceResponse(
        create_sse_generator(stream_func, "Failed to create conversation")
    )


@router.post("/{session_id}/message", response_model=MessageResponse)
@handle_service_errors("send message")
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> MessageResponse:
    """Send a message to a session and get the complete response (non-streaming)."""
    result = await conversation_service.send_message(session_id, request.content)
    return MessageResponse(**result)


@router.post("/{session_id}/stream")
async def stream_message(
    session_id: str,
    request: SendMessageRequest,
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> EventSourceResponse:
    """Send a message and stream the response as Server-Sent Events.

    SSE Events:
        - text_delta: Streaming text chunks
        - tool_use: Tool invocation
        - tool_result: Tool result
        - done: Conversation complete
    """
    def stream_func() -> AsyncIterator[dict[str, Any]]:
        return conversation_service.stream_message(session_id, request.content, request.user_id)

    return EventSourceResponse(
        create_sse_generator(stream_func, "Streaming failed")
    )


@router.post("/{session_id}/interrupt", response_model=InterruptResponse)
@handle_service_errors("interrupt conversation")
async def interrupt_conversation(
    session_id: str,
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> InterruptResponse:
    """Interrupt the current conversation task."""
    await conversation_service.interrupt(session_id)
    return InterruptResponse(
        session_id=session_id,
        message="Conversation interrupted successfully"
    )
