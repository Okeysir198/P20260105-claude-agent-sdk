"""Message conversion utilities for SSE and WebSocket streaming.

Converts Claude Agent SDK Message types to Server-Sent Events (SSE) format
and WebSocket format for streaming responses over HTTP and WebSocket.
"""
import json
from typing import Any, Literal, Optional

from claude_agent_sdk.types import (
    Message,
    SystemMessage,
    StreamEvent,
    AssistantMessage,
    UserMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
)

from api.constants import EventType


def _convert_system_message(msg: SystemMessage, format: Literal["sse", "ws"]) -> Optional[dict]:
    """Convert SystemMessage to event format."""
    if msg.subtype == "init" and hasattr(msg, 'data'):
        session_id = msg.data.get('session_id')
        if session_id:
            if format == "sse":
                return {
                    "event": EventType.SESSION_ID,
                    "data": json.dumps({"session_id": session_id})
                }
            else:  # ws
                return {"type": EventType.SESSION_ID, "session_id": session_id}
    return None


def _convert_stream_event(msg: StreamEvent, format: Literal["sse", "ws"]) -> Optional[dict]:
    """Convert StreamEvent to event format."""
    event = msg.event
    delta = event.get("delta", {})

    if delta.get("type") == "text_delta":
        text = delta.get("text", "")
        if format == "sse":
            return {
                "event": EventType.TEXT_DELTA,
                "data": json.dumps({"text": text})
            }
        else:  # ws
            return {"type": EventType.TEXT_DELTA, "text": text}
    return None


def _convert_assistant_message(msg: AssistantMessage, format: Literal["sse", "ws"]) -> Optional[dict]:
    """Convert AssistantMessage to event format.

    Handles tool_use and tool_result blocks. In streaming mode, text is
    handled by StreamEvent instead.
    """
    for block in msg.content:
        if isinstance(block, ToolUseBlock):
            if format == "sse":
                return {
                    "event": EventType.TOOL_USE,
                    "data": json.dumps({
                        "id": block.id,
                        "name": block.name,
                        "input": block.input if block.input else {}
                    })
                }
            else:  # ws
                return {
                    "type": EventType.TOOL_USE,
                    "id": block.id,
                    "name": block.name,
                    "input": block.input if block.input else {}
                }
        elif isinstance(block, ToolResultBlock):
            # Handle tool result block (primarily for WebSocket)
            content = block.content
            if content is None:
                content = ""
            elif isinstance(content, list):
                content = "\n".join(str(item) for item in content)
            elif not isinstance(content, str):
                content = str(content)

            if format == "sse":
                return {
                    "event": EventType.TOOL_RESULT,
                    "data": json.dumps({
                        "tool_use_id": block.tool_use_id,
                        "content": content,
                        "is_error": block.is_error if hasattr(block, 'is_error') else False
                    })
                }
            else:  # ws
                return {
                    "type": EventType.TOOL_RESULT,
                    "tool_use_id": block.tool_use_id,
                    "content": content,
                    "is_error": block.is_error if hasattr(block, 'is_error') else False
                }
    return None


def _convert_result_message(msg: ResultMessage, format: Literal["sse", "ws"]) -> dict:
    """Convert ResultMessage to event format."""
    if format == "sse":
        return {
            "event": EventType.DONE,
            "data": json.dumps({
                "turn_count": msg.num_turns,
                "total_cost_usd": msg.total_cost_usd or 0.0
            })
        }
    else:  # ws
        return {
            "type": EventType.DONE,
            "turn_count": msg.num_turns,
            "total_cost_usd": msg.total_cost_usd or 0.0
        }


def convert_message(msg: Message, format: Literal["sse", "ws"] = "sse") -> Optional[dict]:
    """Convert SDK Message types to SSE or WebSocket event format.

    Unified converter that handles conversion of various message types from
    the Claude Agent SDK into event dictionaries for streaming.

    Args:
        msg: A Message object from claude_agent_sdk.types
        format: Output format - "sse" for Server-Sent Events (default),
                "ws" for WebSocket JSON

    Returns:
        For SSE format: Dictionary with 'event' and 'data' keys
        For WS format: Dictionary with 'type' key and direct data fields
        Returns None for messages that shouldn't be streamed (like UserMessage)

    Examples:
        >>> msg = SystemMessage(subtype="init", data={"session_id": "abc123"})
        >>> convert_message(msg, format="sse")
        {'event': 'session_id', 'data': '{"session_id": "abc123"}'}
        >>> convert_message(msg, format="ws")
        {'type': 'session_id', 'session_id': 'abc123'}

        >>> msg = StreamEvent(event={"delta": {"type": "text_delta", "text": "Hello"}})
        >>> convert_message(msg, format="sse")
        {'event': 'text_delta', 'data': '{"text": "Hello"}'}
        >>> convert_message(msg, format="ws")
        {'type': 'text_delta', 'text': 'Hello'}
    """
    if isinstance(msg, SystemMessage):
        return _convert_system_message(msg, format)
    elif isinstance(msg, StreamEvent):
        return _convert_stream_event(msg, format)
    elif isinstance(msg, AssistantMessage):
        return _convert_assistant_message(msg, format)
    elif isinstance(msg, UserMessage):
        return None
    elif isinstance(msg, ResultMessage):
        return _convert_result_message(msg, format)

    return None


def convert_message_to_sse(msg: Message) -> dict[str, str] | None:
    """Convert SDK Message types to SSE event format.

    Handles conversion of various message types from the Claude Agent SDK
    into SSE-compatible event dictionaries with 'event' and 'data' fields.

    This is a backward-compatible wrapper around convert_message().

    Args:
        msg: A Message object from claude_agent_sdk.types

    Returns:
        Dictionary with 'event' and 'data' keys, or None for messages
        that shouldn't be streamed (like UserMessage).

    Examples:
        >>> msg = SystemMessage(subtype="init", data={"session_id": "abc123"})
        >>> convert_message_to_sse(msg)
        {'event': 'session_id', 'data': '{"session_id": "abc123"}'}

        >>> msg = StreamEvent(event={"delta": {"type": "text_delta", "text": "Hello"}})
        >>> convert_message_to_sse(msg)
        {'event': 'text_delta', 'data': '{"text": "Hello"}'}
    """
    return convert_message(msg, format="sse")


def message_to_dict(msg: Message) -> Optional[dict]:
    """Convert SDK message to JSON-serializable dict for WebSocket.

    This is a convenience alias for convert_message(msg, format="ws").

    Args:
        msg: A Message object from claude_agent_sdk.types

    Returns:
        Dictionary with 'type' key and direct data fields, or None
        for messages that shouldn't be streamed.
    """
    return convert_message(msg, format="ws")
