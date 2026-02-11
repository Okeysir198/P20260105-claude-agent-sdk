"""Centralized constants for API communication."""

from enum import IntEnum, StrEnum


class EventType(StrEnum):
    """Event types for SSE and WebSocket communication."""
    SESSION_ID = "session_id"
    TEXT_DELTA = "text_delta"
    CONTENT_BLOCK = "content_block"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    DONE = "done"
    ERROR = "error"
    READY = "ready"
    ASK_USER_QUESTION = "ask_user_question"
    USER_ANSWER = "user_answer"
    CANCEL_REQUEST = "cancel_request"
    CANCELLED = "cancelled"
    COMPACT_REQUEST = "compact_request"
    COMPACT_STARTED = "compact_started"
    COMPACT_COMPLETED = "compact_completed"
    THINKING = "thinking"
    ASSISTANT_TEXT = "assistant_text"


class MessageRole(StrEnum):
    """Message roles for conversation history."""
    USER = "user"
    ASSISTANT = "assistant"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    SYSTEM = "system"
    EVENT = "event"


class WSCloseCode(IntEnum):
    """WebSocket close codes for application-specific errors.

    Range 4000-4999 is reserved for application use per RFC 6455.
    """
    AUTH_FAILED = 4001
    SDK_CONNECTION_FAILED = 4002
    SESSION_NOT_FOUND = 4004


# Configuration defaults
ASK_USER_QUESTION_TIMEOUT = 60  # seconds
FIRST_MESSAGE_TRUNCATE_LENGTH = 100
