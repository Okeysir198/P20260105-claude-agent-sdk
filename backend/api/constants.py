"""Centralized event constants for API communication."""

from enum import StrEnum


class EventType(StrEnum):
    """Event types for SSE and WebSocket communication."""
    SESSION_ID = "session_id"
    TEXT_DELTA = "text_delta"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    DONE = "done"
    ERROR = "error"
    READY = "ready"


class MessageRole(StrEnum):
    """Message roles for conversation history."""
    USER = "user"
    ASSISTANT = "assistant"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
