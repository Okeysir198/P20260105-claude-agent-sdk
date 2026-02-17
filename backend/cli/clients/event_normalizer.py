"""Event normalizer for SSE and WebSocket events.

Provides utility functions to normalize events from different transport
protocols to a common internal format for CLI handlers.
"""
from typing import Any

from api.constants import EventType


# Mapping of transport event types to internal EventType constants
EVENT_TYPE_MAP = {
    "session_id": EventType.SESSION_ID,
    "text_delta": EventType.TEXT_DELTA,
    "tool_use": EventType.TOOL_USE,
    "tool_result": EventType.TOOL_RESULT,
    "done": EventType.DONE,
    "error": EventType.ERROR,
    "ready": EventType.READY,
    "ask_user_question": EventType.ASK_USER_QUESTION,
    "cancelled": EventType.CANCELLED,
    "compact_started": EventType.COMPACT_STARTED,
    "compact_completed": EventType.COMPACT_COMPLETED,
    "thinking": EventType.THINKING,
    "assistant_text": EventType.ASSISTANT_TEXT,
}


def normalize_sse_event(event_name: str, data: dict) -> dict | None:
    """Normalize SSE event to common format.

    Args:
        event_name: The SSE event type (e.g., 'text_delta', 'done').
        data: The parsed JSON data from the SSE event.

    Returns:
        Normalized event dictionary, or None if the event should be ignored.
    """
    normalized_type = EVENT_TYPE_MAP.get(event_name, event_name)

    return {
        "type": normalized_type,
        "data": data
    }


def normalize_ws_event(data: dict) -> dict | None:
    """Normalize WebSocket event to common format.

    Args:
        data: The parsed JSON data from the WebSocket message.

    Returns:
        Normalized event dictionary, or None if the event should be ignored.
    """
    event_type = data.get("type", data.get("event"))

    if event_type is None:
        return None

    normalized_type = EVENT_TYPE_MAP.get(event_type, event_type)
    event_data = data.get("data", data)

    return {
        "type": normalized_type,
        "data": event_data
    }


def to_stream_event(text: str) -> dict:
    """Create a stream event for text delta.

    Args:
        text: The text content to wrap.

    Returns:
        Stream event dictionary in CLI format.
    """
    return {
        "type": "stream_event",
        "event": {
            "type": "content_block_delta",
            "delta": {
                "type": "text_delta",
                "text": text
            }
        }
    }


def to_init_event(session_id: str) -> dict:
    """Create an init event with session ID.

    Args:
        session_id: The session ID to include.

    Returns:
        Init event dictionary.
    """
    return {
        "type": "init",
        "session_id": session_id
    }


def to_success_event(num_turns: int, total_cost_usd: float = 0.0) -> dict:
    """Create a success event.

    Args:
        num_turns: Number of conversation turns.
        total_cost_usd: Total cost in USD.

    Returns:
        Success event dictionary.
    """
    return {
        "type": "success",
        "num_turns": num_turns,
        "total_cost_usd": total_cost_usd
    }


def to_error_event(error: str) -> dict:
    """Create an error event.

    Args:
        error: Error message.

    Returns:
        Error event dictionary.
    """
    return {
        "type": "error",
        "error": error
    }


def to_info_event(message: str) -> dict:
    """Create an info event.

    Args:
        message: Info message.

    Returns:
        Info event dictionary.
    """
    return {
        "type": "info",
        "message": message
    }


def to_tool_use_event(name: str, input_data: dict) -> dict:
    """Create a tool use event.

    Args:
        name: Tool name.
        input_data: Tool input data.

    Returns:
        Tool use event dictionary.
    """
    return {
        "type": "tool_use",
        "name": name,
        "input": input_data
    }


def to_cancelled_event() -> dict:
    """Create a cancelled event."""
    return {"type": "cancelled"}


def to_compact_started_event() -> dict:
    """Create a compact started event."""
    return {"type": "compact_started"}


def to_compact_completed_event(summary: str = "") -> dict:
    """Create a compact completed event.

    Args:
        summary: Optional summary of the compaction.
    """
    return {"type": "compact_completed", "summary": summary}


def to_thinking_event(text: str) -> dict:
    """Create a thinking event.

    Args:
        text: The thinking content.
    """
    return {"type": "thinking", "text": text}


def to_assistant_text_event(text: str) -> dict:
    """Create an assistant text event (canonical cleaned text).

    Args:
        text: The cleaned assistant text.
    """
    return {"type": "assistant_text", "text": text}


def to_ask_user_event(question_id: str, questions: list, timeout: int = 60) -> dict:
    """Create an ask user question event.

    Args:
        question_id: Unique ID for the question.
        questions: List of questions to ask.
        timeout: Timeout in seconds.

    Returns:
        Ask user question event dictionary.
    """
    return {
        "type": "ask_user_question",
        "question_id": question_id,
        "questions": questions,
        "timeout": timeout
    }
