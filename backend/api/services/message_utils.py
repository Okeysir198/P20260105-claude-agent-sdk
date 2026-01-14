"""Shared utilities for processing Claude SDK messages.

Provides common functions for converting SDK messages to SSE events
and normalizing tool result content.
"""

from dataclasses import dataclass, field
from typing import Any, Iterator

from claude_agent_sdk.types import (
    Message,
    StreamEvent,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
)


@dataclass
class StreamingContext:
    """Accumulates state during message streaming."""

    accumulated_text: str = ""
    tool_uses: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    turn_count: int = 0
    total_cost: float = 0.0


def normalize_tool_content(content: Any) -> str:
    """Normalize tool result content to a string.

    Args:
        content: Raw tool result content (may be None, str, list, or other)

    Returns:
        Normalized string representation
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(item) for item in content)
    return str(content)


def process_stream_event(event: StreamEvent, ctx: StreamingContext) -> Iterator[dict[str, Any]]:
    """Process a StreamEvent and yield SSE events.

    Args:
        event: StreamEvent from SDK
        ctx: StreamingContext to accumulate text

    Yields:
        SSE event dictionaries for text deltas
    """
    raw_event = event.event
    if raw_event.get("type") != "content_block_delta":
        return

    delta = raw_event.get("delta", {})
    if delta.get("type") != "text_delta":
        return

    text = delta.get("text", "")
    if text:
        ctx.accumulated_text += text
        yield {"event": "text_delta", "data": {"text": text}}


def process_assistant_message(msg: AssistantMessage, ctx: StreamingContext) -> Iterator[dict[str, Any]]:
    """Process an AssistantMessage and yield SSE events for tool uses.

    Args:
        msg: AssistantMessage from SDK
        ctx: StreamingContext to accumulate tool uses

    Yields:
        SSE event dictionaries for tool uses
    """
    for block in msg.content:
        if isinstance(block, ToolUseBlock):
            tool_data = {
                "id": block.id,
                "name": block.name,
                "input": block.input if block.input else {},
            }
            ctx.tool_uses.append(tool_data)
            yield {
                "event": "tool_use",
                "data": {"tool_name": block.name, "input": tool_data["input"]},
            }


def process_user_message(msg: UserMessage, ctx: StreamingContext) -> Iterator[dict[str, Any]]:
    """Process a UserMessage and yield SSE events for tool results.

    Args:
        msg: UserMessage from SDK (contains tool results)
        ctx: StreamingContext to accumulate tool results

    Yields:
        SSE event dictionaries for tool results
    """
    for block in msg.content:
        if isinstance(block, ToolResultBlock):
            content = normalize_tool_content(block.content)
            is_error = getattr(block, "is_error", False)

            result_data = {
                "tool_use_id": block.tool_use_id,
                "content": content,
                "is_error": is_error,
            }
            ctx.tool_results.append(result_data)
            yield {"event": "tool_result", "data": result_data}


def process_result_message(msg: ResultMessage, ctx: StreamingContext) -> None:
    """Process a ResultMessage to extract completion data.

    Args:
        msg: ResultMessage from SDK
        ctx: StreamingContext to store turn count and cost
    """
    ctx.turn_count = msg.num_turns
    ctx.total_cost = msg.total_cost_usd


def process_message(msg: Message, ctx: StreamingContext) -> Iterator[dict[str, Any]]:
    """Process any SDK message type and yield appropriate SSE events.

    Args:
        msg: Any SDK Message type
        ctx: StreamingContext to accumulate state

    Yields:
        SSE event dictionaries based on message type
    """
    if isinstance(msg, StreamEvent):
        yield from process_stream_event(msg, ctx)
    elif isinstance(msg, AssistantMessage):
        yield from process_assistant_message(msg, ctx)
    elif isinstance(msg, UserMessage):
        yield from process_user_message(msg, ctx)
    elif isinstance(msg, ResultMessage):
        process_result_message(msg, ctx)


def convert_message_to_dict(msg: Message) -> dict[str, Any]:
    """Convert SDK message types to API format dictionary.

    Args:
        msg: SDK Message object

    Returns:
        Dictionary representation of the message
    """
    result: dict[str, Any] = {"type": msg.__class__.__name__}

    if isinstance(msg, SystemMessage):
        result["subtype"] = msg.subtype
        result["data"] = msg.data

    elif isinstance(msg, UserMessage):
        result["content"] = _convert_content_blocks(msg.content, for_user=True)

    elif isinstance(msg, AssistantMessage):
        result["content"] = _convert_content_blocks(msg.content, for_user=False)

    elif isinstance(msg, ResultMessage):
        result["subtype"] = msg.subtype
        result["num_turns"] = msg.num_turns
        result["total_cost_usd"] = msg.total_cost_usd

    elif isinstance(msg, StreamEvent):
        result["event"] = msg.event

    return result


def _convert_content_blocks(blocks: list, for_user: bool) -> list[dict[str, Any]]:
    """Convert content blocks to dictionary format.

    Args:
        blocks: List of content blocks
        for_user: True if blocks are from UserMessage, False for AssistantMessage

    Returns:
        List of converted block dictionaries
    """
    content_list = []
    for block in blocks:
        if isinstance(block, TextBlock):
            content_list.append({"type": "text", "text": block.text})
        elif isinstance(block, ToolResultBlock) and for_user:
            content_list.append({
                "type": "tool_result",
                "tool_use_id": block.tool_use_id,
                "content": block.content,
            })
        elif isinstance(block, ToolUseBlock) and not for_user:
            content_list.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })
    return content_list
