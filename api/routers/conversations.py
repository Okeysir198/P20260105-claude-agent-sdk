"""Conversation endpoints for message handling."""

import json
from typing import Any, AsyncIterator, Callable
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from api.dependencies import get_conversation_service
from api.services.conversation_service import ConversationService


router = APIRouter(tags=["conversations"])


# Request/Response Models
class CreateConversationRequest(BaseModel):
    """Request model for creating a conversation with first message."""
    content: str
    resume_session_id: str | None = None


class SendMessageRequest(BaseModel):
    """Request model for sending a message."""
    content: str


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


# Utility Functions
async def create_sse_event_generator(
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
    try:
        async for event_data in stream_func():
            event_type = event_data.get("event", "message")
            data = event_data.get("data", {})

            yield {
                "event": event_type,
                "data": json.dumps(data)
            }

    except ValueError as e:
        yield {
            "event": "error",
            "data": json.dumps({"error": str(e)})
        }
    except Exception as e:
        yield {
            "event": "error",
            "data": json.dumps({"error": f"{error_prefix}: {str(e)}"})
        }


# Endpoints
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: CreateConversationRequest,
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> EventSourceResponse:
    """Create a new conversation and send the first message.

    This endpoint combines session creation with the first message,
    ensuring only real session IDs from the SDK are ever exposed.

    Args:
        request: Conversation creation request with first message
        conversation_service: Conversation service dependency

    Returns:
        EventSourceResponse with SSE stream including session_id

    SSE Event Format:
        - event: session_id - Real session ID from SDK
          data: {"session_id": "uuid-from-sdk"}

        - event: text_delta - Streaming text chunks
          data: {"text": "..."}

        - event: tool_use - Tool invocation
          data: {"tool_name": "...", "input": {...}}

        - event: tool_result - Tool result
          data: {"content": "..."}

        - event: done - Conversation complete
          data: {"session_id": "...", "turn_count": N}
    """
    def stream_func():
        return conversation_service.create_and_stream(
            request.content,
            request.resume_session_id
        )

    return EventSourceResponse(
        create_sse_event_generator(stream_func, "Failed to create conversation")
    )


@router.post("/{session_id}/message", response_model=MessageResponse)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> MessageResponse:
    """Send a message to a session and get the complete response (non-streaming).

    Args:
        session_id: Session ID
        request: Message request
        conversation_service: Conversation service dependency

    Returns:
        Complete message response

    Raises:
        HTTPException: If session not found or message fails
    """
    try:
        result = await conversation_service.send_message(session_id, request.content)
        return MessageResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )


@router.post("/{session_id}/stream")
async def stream_message(
    session_id: str,
    request: SendMessageRequest,
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> EventSourceResponse:
    """Send a message and stream the response as Server-Sent Events.

    Args:
        session_id: Session ID
        request: Message request
        conversation_service: Conversation service dependency

    Returns:
        EventSourceResponse with SSE stream

    Raises:
        HTTPException: If session not found or streaming fails

    SSE Event Format:
        - event: text_delta - Streaming text chunks
          data: {"text": "..."}

        - event: tool_use - Tool invocation
          data: {"tool_name": "...", "input": {...}}

        - event: tool_result - Tool result
          data: {"content": "..."}

        - event: done - Conversation complete
          data: {"turn_count": N}
    """
    def stream_func():
        return conversation_service.stream_message(session_id, request.content)

    return EventSourceResponse(
        create_sse_event_generator(stream_func, "Streaming failed")
    )


@router.post("/{session_id}/interrupt", response_model=InterruptResponse)
async def interrupt_conversation(
    session_id: str,
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> InterruptResponse:
    """Interrupt the current conversation task.

    Args:
        session_id: Session ID
        conversation_service: Conversation service dependency

    Returns:
        Interrupt confirmation

    Raises:
        HTTPException: If session not found or interrupt fails
    """
    try:
        await conversation_service.interrupt(session_id)
        return InterruptResponse(
            session_id=session_id,
            message="Conversation interrupted successfully"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to interrupt conversation: {str(e)}"
        )
