"""Message conversion utilities for SSE and WebSocket streaming.

Converts Claude Agent SDK Message types to Server-Sent Events (SSE) format
and WebSocket format for streaming responses over HTTP and WebSocket.

This module is designed for portability - it only depends on:
- claude_agent_sdk.types for message types
- api.constants for event type definitions
"""
import json
from typing import Any, Iterator, Literal, Optional

from claude_agent_sdk.types import (
    AssistantMessage,
    Message,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from api.constants import EventType

# Type alias for output format
OutputFormat = Literal["sse", "ws"]


def _format_event(
    event_type: str,
    data: dict[str, Any],
    output_format: OutputFormat
) -> dict[str, Any]:
    """Format event data for SSE or WebSocket output.

    Args:
        event_type: The event type string (from EventType enum).
        data: The event payload data.
        output_format: Target format - "sse" or "ws".

    Returns:
        Formatted event dictionary.
    """
    if output_format == "sse":
        return {"event": event_type, "data": json.dumps(data)}
    return {"type": event_type, **data}


def _normalize_tool_result_content(content: Any) -> str:
    """Normalize tool result content to string format."""
    if content is None:
        return ""
    if isinstance(content, list):
        return "\n".join(str(item) for item in content)
    if not isinstance(content, str):
        return str(content)
    return content


def _convert_system_message(
    msg: SystemMessage,
    output_format: OutputFormat
) -> Optional[dict[str, Any]]:
    """Convert SystemMessage to event format."""
    if msg.subtype != "init" or not hasattr(msg, "data"):
        return None

    session_id = msg.data.get("session_id")
    if not session_id:
        return None

    return _format_event(EventType.SESSION_ID, {"session_id": session_id}, output_format)


def _convert_stream_event(
    msg: StreamEvent,
    output_format: OutputFormat
) -> Optional[dict[str, Any]]:
    """Convert StreamEvent to event format.

    Handles text_delta and tool_result deltas from the SDK.
    """
    delta = msg.event.get("delta", {})
    delta_type = delta.get("type")

    if delta_type == "text_delta":
        return _format_event(
            EventType.TEXT_DELTA,
            {"text": delta.get("text", "")},
            output_format
        )
    elif delta_type == "tool_result":
        # StreamEvent can contain tool_result deltas with tool_use_id and content
        return _format_event(
            EventType.TOOL_RESULT,
            {
                "tool_use_id": delta.get("tool_use_id"),
                "content": _normalize_tool_result_content(delta.get("content")),
                "is_error": delta.get("is_error", False)
            },
            output_format
        )

    return None


def _convert_tool_use_block(
    block: ToolUseBlock,
    output_format: OutputFormat
) -> dict[str, Any]:
    """Convert ToolUseBlock to event format."""
    return _format_event(
        EventType.TOOL_USE,
        {"id": block.id, "name": block.name, "input": block.input or {}},
        output_format
    )


def _convert_tool_result_block(
    block: ToolResultBlock,
    output_format: OutputFormat
) -> dict[str, Any]:
    """Convert ToolResultBlock to event format."""
    return _format_event(
        EventType.TOOL_RESULT,
        {
            "tool_use_id": block.tool_use_id,
            "content": _normalize_tool_result_content(block.content),
            "is_error": getattr(block, "is_error", False)
        },
        output_format
    )


def _convert_assistant_message(
    msg: AssistantMessage,
    output_format: OutputFormat
) -> Optional[dict[str, Any]]:
    """Convert AssistantMessage to event format.

    Handles tool_use and tool_result blocks. In streaming mode, text is
    handled by StreamEvent instead.
    """
    for block in msg.content:
        if isinstance(block, ToolUseBlock):
            return _convert_tool_use_block(block, output_format)
        if isinstance(block, ToolResultBlock):
            return _convert_tool_result_block(block, output_format)
    return None


def _convert_result_message(
    msg: ResultMessage,
    output_format: OutputFormat
) -> dict[str, Any]:
    """Convert ResultMessage to event format."""
    return _format_event(
        EventType.DONE,
        {"turn_count": msg.num_turns, "total_cost_usd": msg.total_cost_usd or 0.0},
        output_format
    )


# Message type to converter mapping for dispatch
_MESSAGE_CONVERTERS: dict[type, Any] = {
    SystemMessage: _convert_system_message,
    StreamEvent: _convert_stream_event,
    AssistantMessage: _convert_assistant_message,
    ResultMessage: _convert_result_message,
}


def _convert_user_message(
    msg: UserMessage,
    output_format: OutputFormat
) -> list[dict[str, Any]]:
    """Convert UserMessage to event format(s).

    UserMessage contains tool_result blocks after tool execution.
    Can contain multiple blocks, so returns a list.
    """
    events = []
    for block in msg.content:
        if isinstance(block, ToolResultBlock):
            events.append(_convert_tool_result_block(block, output_format))
    return events


def convert_messages(
    msg: Message,
    output_format: OutputFormat = "sse"
) -> Iterator[dict[str, Any]]:
    """Generator that yields one or more events from a SDK message.

    This is the preferred function for message conversion as it properly
    handles UserMessage which can contain multiple tool_result blocks.

    Args:
        msg: A Message object from claude_agent_sdk.types.
        output_format: Target format - "sse" or "ws".

    Yields:
        Event dictionaries for streaming.
    """
    if isinstance(msg, UserMessage):
        for event in _convert_user_message(msg, output_format):
            yield event
        return

    converter = _MESSAGE_CONVERTERS.get(type(msg))
    if converter:
        result = converter(msg, output_format)
        if result:
            yield result


def convert_message(
    msg: Message,
    output_format: OutputFormat = "sse"
) -> Optional[dict[str, Any]]:
    """Convert SDK Message types to SSE or WebSocket event format.

    Unified converter that handles conversion of various message types from
    the Claude Agent SDK into event dictionaries for streaming.

    Args:
        msg: A Message object from claude_agent_sdk.types.
        output_format: Output format - "sse" for Server-Sent Events (default),
                       "ws" for WebSocket JSON.

    Returns:
        For SSE format: Dictionary with 'event' and 'data' keys.
        For WS format: Dictionary with 'type' key and direct data fields.
        Returns None for messages that shouldn't be streamed (like UserMessage).

    Examples:
        >>> msg = SystemMessage(subtype="init", data={"session_id": "abc123"})
        >>> convert_message(msg, output_format="sse")
        {'event': 'session_id', 'data': '{"session_id": "abc123"}'}
        >>> convert_message(msg, output_format="ws")
        {'type': 'session_id', 'session_id': 'abc123'}
    """
    if isinstance(msg, UserMessage):
        return None

    converter = _MESSAGE_CONVERTERS.get(type(msg))
    if converter:
        return converter(msg, output_format)

    return None


def convert_message_to_sse(msg: Message) -> Optional[dict[str, str]]:
    """Convert SDK Message types to SSE event format.

    Backward-compatible wrapper around convert_message().
    """
    return convert_message(msg, output_format="sse")


def message_to_dict(msg: Message) -> Optional[dict[str, Any]]:
    """Convert SDK message to JSON-serializable dict for WebSocket.

    Convenience alias for convert_message(msg, output_format="ws").

    Note: This returns only the first event. For messages that may contain
    multiple events (like UserMessage with tool_result blocks), use
    message_to_dicts() instead.
    """
    return convert_message(msg, output_format="ws")


def message_to_dicts(msg: Message) -> list[dict[str, Any]]:
    """Convert SDK message to list of dicts for WebSocket.

    This function properly handles UserMessage which can contain multiple
    tool_result blocks.

    Args:
        msg: A Message object from claude_agent_sdk.types.

    Returns:
        List of event dictionaries for WebSocket streaming.
    """
    return list(convert_messages(msg, output_format="ws"))


def convert_messages_to_sse(msg: Message) -> list[dict[str, str]]:
    """Convert SDK message to list of SSE events.

    This function properly handles UserMessage which can contain multiple
    tool_result blocks.

    Args:
        msg: A Message object from claude_agent_sdk.types.

    Returns:
        List of SSE event dictionaries with 'event' and 'data' keys.
    """
    return list(convert_messages(msg, output_format="sse"))
