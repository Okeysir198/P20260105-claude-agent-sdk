"""Message conversion utilities for SSE streaming.

Converts Claude Agent SDK Message types to Server-Sent Events (SSE) format
for streaming responses over HTTP.
"""
import json
from typing import Any

from claude_agent_sdk.types import (
    Message,
    SystemMessage,
    StreamEvent,
    AssistantMessage,
    UserMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)


def convert_message_to_sse(msg: Message) -> dict[str, str] | None:
    """Convert SDK Message types to SSE event format.

    Handles conversion of various message types from the Claude Agent SDK
    into SSE-compatible event dictionaries with 'event' and 'data' fields.

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
    # SystemMessage with subtype="init" -> emit session_id event
    if isinstance(msg, SystemMessage):
        if msg.subtype == "init" and hasattr(msg, 'data'):
            session_id = msg.data.get('session_id')
            if session_id:
                return {
                    "event": "session_id",
                    "data": json.dumps({"session_id": session_id})
                }
        # Other system messages are not streamed
        return None

    # StreamEvent -> check for text_delta in delta
    elif isinstance(msg, StreamEvent):
        event = msg.event
        delta = event.get("delta", {})

        if delta.get("type") == "text_delta":
            text = delta.get("text", "")
            return {
                "event": "text_delta",
                "data": json.dumps({"text": text})
            }

        # Other stream events are not converted
        return None

    # AssistantMessage -> emit text_delta and tool_use events
    elif isinstance(msg, AssistantMessage):
        # Note: This is for non-streaming mode. In streaming mode with
        # include_partial_messages=True, text comes via StreamEvent instead.
        # We only handle tool_use blocks here since text is handled by StreamEvent.
        tool_use_blocks = [
            block for block in msg.content
            if isinstance(block, ToolUseBlock)
        ]

        if tool_use_blocks:
            # Return first tool_use block (caller will iterate if needed)
            block = tool_use_blocks[0]
            return {
                "event": "tool_use",
                "data": json.dumps({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input if block.input else {}
                })
            }

        # Text blocks in AssistantMessage are handled by StreamEvent in streaming mode
        # and don't need separate SSE events here
        return None

    # UserMessage -> not streamed to client
    elif isinstance(msg, UserMessage):
        return None

    # ResultMessage -> emit done event with session stats
    elif isinstance(msg, ResultMessage):
        return {
            "event": "done",
            "data": json.dumps({
                "turn_count": msg.num_turns,
                "total_cost_usd": msg.total_cost_usd or 0.0
            })
        }

    # Unknown message types -> not streamed
    return None
