"""Message conversion utilities for SSE and WebSocket streaming.

Converts Claude Agent SDK Message types to Server-Sent Events (SSE) format
and WebSocket format for streaming responses over HTTP and WebSocket.

This module is designed for portability - it only depends on:
- claude_agent_sdk.types for message types
- api.constants for event type definitions
"""
import json
from collections.abc import Iterator
from typing import Any

from claude_agent_sdk.types import (
    AssistantMessage,
    Message,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from api.constants import EventType

# Type alias for output format
OutputFormat = str  # "sse" or "ws"


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
) -> dict[str, Any] | None:
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
) -> dict[str, Any] | None:
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
) -> dict[str, Any] | None:
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


def _convert_text_block(
    block: TextBlock | dict[str, Any],
    output_format: OutputFormat
) -> dict[str, Any]:
    """Convert TextBlock or text dict to event format.

    Args:
        block: TextBlock instance or dict with type='text'.
        output_format: Target format - "sse" or "ws".

    Returns:
        Event dictionary with text content.
    """
    # Handle both TextBlock instances and dict format
    if isinstance(block, TextBlock):
        text = block.text
    else:
        text = block.get("text", "")

    return _format_event(
        EventType.TEXT_DELTA,
        {"text": text},
        output_format
    )


def _convert_image_block(
    block: dict[str, Any],
    output_format: OutputFormat
) -> dict[str, Any]:
    """Convert image block dict to event format.

    Args:
        block: Dict with type='image' and source field.
        output_format: Target format - "sse" or "ws".

    Returns:
        Event dictionary with image content.

    Raises:
        ValueError: If image block is invalid.
    """
    if not isinstance(block, dict):
        raise ValueError(f"Image block must be a dict, got {type(block).__name__}")

    block_type = block.get("type")
    if block_type != "image":
        raise ValueError(f"Expected image block, got type '{block_type}'")

    source = block.get("source")
    if not source or not isinstance(source, dict):
        raise ValueError("Image block must have a source dict")

    # Nest the block to preserve its structure without conflicting with event type
    return _format_event(
        EventType.CONTENT_BLOCK,
        {"block": block},
        output_format
    )


def _convert_user_message(
    msg: UserMessage,
    output_format: OutputFormat
) -> list[dict[str, Any]]:
    """Convert UserMessage to event format(s).

    UserMessage can contain multiple content blocks after tool execution or
    when the user sends multi-part content (text, images, etc.).

    Handles:
    - ToolResultBlock: Tool execution results
    - TextBlock: Text content blocks
    - Image blocks (dict format): Image content with source data
    - Plain string content: Legacy backward compatibility

    Args:
        msg: UserMessage instance from SDK.
        output_format: Target format - "sse" or "ws".

    Returns:
        List of event dictionaries. May be empty if content contains only
        unsupported block types.

    Examples:
        >>> # UserMessage with tool results (WebSocket format)
        >>> msg = UserMessage(content=[ToolResultBlock(tool_use_id="tool-123", content="Success", is_error=False)])
        >>> _convert_user_message(msg, "ws")
        [{'type': 'tool_result', 'tool_use_id': 'tool-123', 'content': 'Success', 'is_error': False}]

        >>> # UserMessage with text and images (WebSocket format)
        >>> msg = UserMessage(content=[
        ...     TextBlock(text="Hello"),
        ...     {"type": "image", "source": {"type": "url", "url": "https://example.com/image.png"}}
        ... ])
        >>> _convert_user_message(msg, "ws")
        [{'type': 'text_delta', 'text': 'Hello'}, {'type': 'content_block', 'block': {'type': 'image', 'source': {...}}}]

        >>> # UserMessage with simple string content (backward compatibility)
        >>> msg = UserMessage(content="Hello world")
        >>> _convert_user_message(msg, "sse")
        [{'event': 'text_delta', 'data': '{"text": "Hello world"}'}]
    """
    events = []

    # Handle legacy string content (backward compatibility)
    if isinstance(msg.content, str):
        events.append(_convert_text_block(TextBlock(text=msg.content), output_format))
        return events

    # Handle list of content blocks
    for block in msg.content:
        # ToolResultBlock - tool execution results
        if isinstance(block, ToolResultBlock):
            events.append(_convert_tool_result_block(block, output_format))

        # TextBlock - text content
        elif isinstance(block, TextBlock):
            events.append(_convert_text_block(block, output_format))

        # Image block (dict format with type='image')
        elif isinstance(block, dict) and block.get("type") == "image":
            try:
                events.append(_convert_image_block(block, output_format))
            except ValueError as e:
                # Log error but continue processing other blocks
                import logging
                logging.getLogger(__name__).warning(f"Failed to convert image block: {e}")

        # Text block as dict (e.g., {"type": "text", "text": "..."})
        elif isinstance(block, dict) and block.get("type") == "text":
            events.append(_convert_text_block(block, output_format))

        # Other block types are ignored (ThinkingBlock, ToolUseBlock in UserMessage context)
        else:
            import logging
            logging.getLogger(__name__).debug(
                f"Skipping unsupported block type in UserMessage: {type(block).__name__}"
            )

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
) -> dict[str, Any] | None:
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


def convert_message_to_sse(msg: Message) -> dict[str, str] | None:
    """Convert SDK Message types to SSE event format.

    Backward-compatible wrapper around convert_message().
    """
    return convert_message(msg, output_format="sse")


def message_to_dict(msg: Message) -> dict[str, Any] | None:
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
