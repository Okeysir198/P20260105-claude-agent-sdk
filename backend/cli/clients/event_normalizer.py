"""Event normalizer for SSE and WebSocket events.

Provides utility functions to normalize events from different transport
protocols to a common internal format for CLI handlers.
"""
from typing import Any

from api.constants import EventType


def normalize_sse_event(event_name: str, data: dict) -> dict | None:
    """Normalize SSE event to common format.

    Converts SSE event format to a standardized internal representation
    that can be processed uniformly by CLI handlers.

    Args:
        event_name: The SSE event type (e.g., 'text_delta', 'done').
        data: The parsed JSON data from the SSE event.

    Returns:
        Normalized event dictionary with 'type' and 'data' keys,
        or None if the event should be ignored.
    """
    # Map SSE event names to EventType constants where applicable
    event_type_map = {
        "session_id": EventType.SESSION_ID,
        "text_delta": EventType.TEXT_DELTA,
        "tool_use": EventType.TOOL_USE,
        "tool_result": EventType.TOOL_RESULT,
        "done": EventType.DONE,
        "error": EventType.ERROR,
        "ready": EventType.READY,
    }

    normalized_type = event_type_map.get(event_name, event_name)

    return {
        "type": normalized_type,
        "data": data
    }


def normalize_ws_event(data: dict) -> dict | None:
    """Normalize WebSocket event to common format.

    Converts WebSocket message format to a standardized internal representation
    that can be processed uniformly by CLI handlers.

    Args:
        data: The parsed JSON data from the WebSocket message.

    Returns:
        Normalized event dictionary with 'type' and 'data' keys,
        or None if the event should be ignored.
    """
    # WebSocket events have type in the message itself
    event_type = data.get("type", data.get("event"))

    if event_type is None:
        return None

    # Map WebSocket event types to EventType constants where applicable
    event_type_map = {
        "session_id": EventType.SESSION_ID,
        "text_delta": EventType.TEXT_DELTA,
        "tool_use": EventType.TOOL_USE,
        "tool_result": EventType.TOOL_RESULT,
        "done": EventType.DONE,
        "error": EventType.ERROR,
        "ready": EventType.READY,
    }

    normalized_type = event_type_map.get(event_type, event_type)

    # Extract the data payload - for WebSocket, the data might be in 'data' key
    # or the entire message might be the data
    event_data = data.get("data", data)

    return {
        "type": normalized_type,
        "data": event_data
    }
