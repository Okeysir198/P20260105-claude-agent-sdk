"""Message conversion utilities for SSE and WebSocket streaming."""
import json
import logging
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
from api.services.content_normalizer import normalize_tool_result_content

logger = logging.getLogger(__name__)

OutputFormat = str  # "sse" or "ws"


def _format_event(
    event_type: str,
    data: dict[str, Any],
    output_format: OutputFormat
) -> dict[str, Any]:
    """Format event data for SSE or WebSocket output."""
    if output_format == "sse":
        return {"event": event_type, "data": json.dumps(data)}
    return {"type": event_type, **data}


def _extract_text_from_block(block: Any) -> str:
    """Extract text from a content block (dict with type='text' or TextBlock)."""
    if isinstance(block, dict):
        if block.get("type") == "text":
            return block.get("text", "")
    if isinstance(block, TextBlock):
        return block.text
    return str(block)


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
    """Convert StreamEvent to event format."""
    delta = msg.event.get("delta", {})
    delta_type = delta.get("type")

    if delta_type == "text_delta":
        return _format_event(
            EventType.TEXT_DELTA,
            {"text": delta.get("text", "")},
            output_format
        )
    elif delta_type == "tool_result":
        return _format_event(
            EventType.TOOL_RESULT,
            {
                "tool_use_id": delta.get("tool_use_id"),
                "content": normalize_tool_result_content(delta.get("content")),
                "is_error": delta.get("is_error", False)
            },
            output_format
        )

    return None


def _convert_tool_use_block(
    block: ToolUseBlock,
    output_format: OutputFormat,
    parent_tool_use_id: str | None = None,
) -> dict[str, Any]:
    """Convert ToolUseBlock to event format."""
    data = {"id": block.id, "name": block.name, "input": block.input or {}}
    if parent_tool_use_id:
        data["parent_tool_use_id"] = parent_tool_use_id
    return _format_event(EventType.TOOL_USE, data, output_format)


def _convert_tool_result_block(
    block: ToolResultBlock,
    output_format: OutputFormat,
    parent_tool_use_id: str | None = None,
) -> dict[str, Any]:
    """Convert ToolResultBlock to event format."""
    data = {
        "tool_use_id": block.tool_use_id,
        "content": normalize_tool_result_content(block.content),
        "is_error": getattr(block, "is_error", False)
    }
    if parent_tool_use_id:
        data["parent_tool_use_id"] = parent_tool_use_id
    return _format_event(EventType.TOOL_RESULT, data, output_format)


def _convert_assistant_message(
    msg: AssistantMessage,
    output_format: OutputFormat
) -> list[dict[str, Any]]:
    """Convert AssistantMessage to event format(s). TextBlock is skipped (delivered via text_delta)."""
    events = []

    for block in msg.content:
        if isinstance(block, ToolUseBlock):
            events.append(_convert_tool_use_block(block, output_format, msg.parent_tool_use_id))
        elif isinstance(block, ToolResultBlock):
            events.append(_convert_tool_result_block(block, output_format, msg.parent_tool_use_id))
        elif isinstance(block, TextBlock):
            continue
        else:
            # Unknown block type: serialize its attributes as a content_block event
            block_class_name = type(block).__name__
            try:
                if hasattr(block, "__dict__"):
                    attrs = {
                        k: v for k, v in block.__dict__.items()
                        if not k.startswith("_")
                    }
                else:
                    attrs = {}
                block_data = {"type": block_class_name, **attrs}
                events.append(_format_event(
                    EventType.CONTENT_BLOCK,
                    {"block": block_data},
                    output_format
                ))
            except (TypeError, ValueError) as e:
                logger.warning(
                    f"Failed to serialize unknown block type {block_class_name}: {e}"
                )

    return events


def _convert_unknown_message(
    msg: Message,
    output_format: OutputFormat
) -> dict[str, Any] | None:
    """Convert an unknown SDK message type to a generic content_block event."""
    class_name = type(msg).__name__
    sdk_type = f"sdk_{class_name.lower()}"

    try:
        if hasattr(msg, "__dict__"):
            attrs = {
                k: v for k, v in msg.__dict__.items()
                if not k.startswith("_")
            }
        else:
            attrs = {}

        data = {"sdk_type": sdk_type, **attrs}
        return _format_event(EventType.CONTENT_BLOCK, data, output_format)
    except (TypeError, ValueError) as e:
        logger.warning(f"Failed to serialize unknown message type {class_name}: {e}")
        return None


def _convert_result_message(
    msg: ResultMessage,
    output_format: OutputFormat
) -> dict[str, Any]:
    """Convert ResultMessage to event format with cost and usage data."""
    logger.info(
        f"[ResultMessage] cost={msg.total_cost_usd}, "
        f"usage_keys={list(msg.usage.keys()) if msg.usage else None}, "
        f"duration={msg.duration_ms}ms, turns={msg.num_turns}"
    )
    data: dict[str, Any] = {
        "turn_count": msg.num_turns,
        "total_cost_usd": msg.total_cost_usd or 0.0,
        "duration_ms": msg.duration_ms,
        "duration_api_ms": msg.duration_api_ms,
        "is_error": msg.is_error,
    }
    if msg.usage:
        data["usage"] = msg.usage
    return _format_event(EventType.DONE, data, output_format)


# Message type to converter mapping for dispatch
# Note: AssistantMessage is handled explicitly in convert_messages() since it returns a list.
_MESSAGE_CONVERTERS: dict[type, Any] = {
    SystemMessage: _convert_system_message,
    StreamEvent: _convert_stream_event,
    ResultMessage: _convert_result_message,
}


def _convert_text_block(
    block: TextBlock | dict[str, Any],
    output_format: OutputFormat
) -> dict[str, Any]:
    """Convert TextBlock or text dict to event format."""
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
    """Convert image block dict to event format."""
    if not isinstance(block, dict):
        raise ValueError(f"Image block must be a dict, got {type(block).__name__}")

    block_type = block.get("type")
    if block_type != "image":
        raise ValueError(f"Expected image block, got type '{block_type}'")

    source = block.get("source")
    if not source or not isinstance(source, dict):
        raise ValueError("Image block must have a source dict")

    return _format_event(
        EventType.CONTENT_BLOCK,
        {"block": block},
        output_format
    )


def _convert_user_message(
    msg: UserMessage,
    output_format: OutputFormat
) -> list[dict[str, Any]]:
    """Convert UserMessage to event format(s)."""
    events = []

    if isinstance(msg.content, str):
        events.append(_convert_text_block(TextBlock(text=msg.content), output_format))
        return events

    for block in msg.content:
        if isinstance(block, ToolResultBlock):
            events.append(_convert_tool_result_block(block, output_format, msg.parent_tool_use_id))
        elif isinstance(block, TextBlock):
            events.append(_convert_text_block(block, output_format))
        elif isinstance(block, dict) and block.get("type") == "image":
            try:
                events.append(_convert_image_block(block, output_format))
            except ValueError as e:
                logger.warning(f"Failed to convert image block: {e}")
        elif isinstance(block, dict) and block.get("type") == "text":
            events.append(_convert_text_block(block, output_format))
        else:
            logger.debug(
                f"Skipping unsupported block type in UserMessage: {type(block).__name__}"
            )

    return events


def convert_messages(
    msg: Message,
    output_format: OutputFormat = "sse"
) -> Iterator[dict[str, Any]]:
    """Yield one or more events from an SDK message."""
    if isinstance(msg, UserMessage):
        for event in _convert_user_message(msg, output_format):
            yield event
        return

    if isinstance(msg, AssistantMessage):
        for event in _convert_assistant_message(msg, output_format):
            yield event
        return

    converter = _MESSAGE_CONVERTERS.get(type(msg))
    if converter:
        result = converter(msg, output_format)
        if result:
            yield result
        return

    result = _convert_unknown_message(msg, output_format)
    if result:
        yield result


def message_to_dicts(msg: Message) -> list[dict[str, Any]]:
    """Convert SDK message to list of dicts for WebSocket."""
    return list(convert_messages(msg, output_format="ws"))


def convert_messages_to_sse(msg: Message) -> list[dict[str, str]]:
    """Convert SDK message to list of SSE events."""
    return list(convert_messages(msg, output_format="sse"))
