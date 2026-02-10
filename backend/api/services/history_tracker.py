"""Centralized history tracking for conversation events.

This module provides a HistoryTracker class that handles all history-related
operations during conversation streaming, including accumulating text deltas,
saving tool events, and finalizing assistant responses.
"""
import json
from dataclasses import dataclass, field
from typing import Any

from agent.core.storage import HistoryStorage
from api.constants import EventType, MessageRole
from api.services.content_normalizer import ContentBlock, normalize_content

# Control/protocol events that should not be persisted to history.
# These are transient signals used for connection and flow management only.
_CONTROL_EVENT_TYPES: set[str] = {
    EventType.SESSION_ID,
    EventType.READY,
    EventType.COMPACT_STARTED,
    EventType.COMPACT_COMPLETED,
    EventType.COMPACT_REQUEST,
    EventType.CANCEL_REQUEST,
}


@dataclass
class HistoryTracker:
    """Tracks and persists conversation history during streaming.

    Handles accumulating text deltas, saving tool events, and finalizing
    assistant responses to the history storage.

    Attributes:
        session_id: The session ID to track history for.
        history: The HistoryStorage instance for persistence.
    """
    session_id: str
    history: HistoryStorage
    _text_parts: list[str] = field(default_factory=list)

    def save_user_message(self, content: str | list[ContentBlock | dict[str, Any]]) -> None:
        """Save a user message to history.

        Supports dual-mode content for backward compatibility:
        - Plain string: Stored as-is (legacy format)
        - list[ContentBlock] | list[dict]: Multi-part content with text/images

        Multi-part content is stored as a list of dicts in the JSONL history file.
        When reading back, the ContentBlock structure is preserved, allowing full
        reconstruction of complex messages with images.

        Args:
            content: The user's message content as:
                - str: Plain text message (backward compatible)
                - list[ContentBlock]: Normalized content blocks
                - list[dict]: Raw content blocks (will be normalized)

        Examples:
            >>> # Legacy string format
            >>> tracker.save_user_message("Hello world")

            >>> # Multi-part with image
            >>> tracker.save_user_message([
            ...     {"type": "text", "text": "Check this out:"},
            ...     {"type": "image", "source": {"type": "url", "url": "https://..."}}
            ... ])
        """
        # Convert content to JSON-serializable format
        if isinstance(content, str):
            # Legacy format: store as string
            serialized_content = content
        else:
            # Multi-part format: convert to list of dicts
            # Check if already ContentBlock objects
            if content and hasattr(content[0], 'model_dump'):
                # Already ContentBlock objects - just serialize
                serialized_content = [block.model_dump() for block in content]
            else:
                # Raw dicts - normalize first
                normalized_blocks = normalize_content(content)
                serialized_content = [block.model_dump() for block in normalized_blocks]

        self.history.append_message(
            session_id=self.session_id,
            role=MessageRole.USER,
            content=serialized_content
        )

    def accumulate_text(self, text: str) -> None:
        """Accumulate text delta parts.

        Args:
            text: A text fragment to accumulate.
        """
        self._text_parts.append(text)

    def get_accumulated_text(self) -> str:
        """Get the accumulated text without clearing it.

        Returns:
            The accumulated text joined together.
        """
        return "".join(self._text_parts)

    def has_accumulated_text(self) -> bool:
        """Check if there is any accumulated text.

        Returns:
            True if text has been accumulated.
        """
        return bool(self._text_parts)

    def save_tool_use(self, data: dict) -> None:
        """Save a tool use event to history.

        Args:
            data: Tool use data containing tool_name, tool_use_id/id, and input.
        """
        metadata = {}
        if data.get("parent_tool_use_id"):
            metadata["parent_tool_use_id"] = data["parent_tool_use_id"]
        self.history.append_message(
            session_id=self.session_id,
            role=MessageRole.TOOL_USE,
            content=json.dumps(data.get("input", {})),
            tool_name=data.get("tool_name") or data.get("name"),
            tool_use_id=data.get("tool_use_id") or data.get("id"),
            metadata=metadata or None,
        )

    def save_tool_result(self, data: dict) -> None:
        """Save a tool result event to history.

        Args:
            data: Tool result data containing tool_use_id, content, and is_error.
        """
        metadata = {}
        if data.get("parent_tool_use_id"):
            metadata["parent_tool_use_id"] = data["parent_tool_use_id"]
        self.history.append_message(
            session_id=self.session_id,
            role=MessageRole.TOOL_RESULT,
            content=str(data.get("content", "")),
            tool_use_id=data.get("tool_use_id"),
            is_error=data.get("is_error", False),
            metadata=metadata or None,
        )

    def save_user_answer(self, data: dict) -> None:
        """Save a user_answer event to history as tool_result.

        Args:
            data: Answer data containing question_id and answers.
        """
        self.history.append_message(
            session_id=self.session_id,
            role=MessageRole.TOOL_RESULT,
            content=json.dumps(data.get("answers", {})),
            tool_use_id=data.get("question_id"),
            is_error=False
        )

    def save_result_message(self, data: dict) -> None:
        """Save a ResultMessage with cost and turn data as a system message.

        Captures the SDK's result metadata (token usage, costs, turn count, etc.)
        so that conversation analytics can be reconstructed from history.

        Args:
            data: Result data dictionary, typically containing fields like
                  cost_usd, input_tokens, output_tokens, num_turns, etc.
        """
        metadata = {"event_type": "result"}
        metadata.update(data)
        self.history.append_message(
            session_id=self.session_id,
            role=MessageRole.SYSTEM,
            content=json.dumps(data),
            metadata=metadata
        )

    def save_generic_event(self, event_type: str, data: dict) -> None:
        """Save an unrecognized SDK event for future analysis.

        Any event type not explicitly handled by this tracker (and not in the
        control-event exclusion set) is persisted as an ``event`` role message
        so that new SDK message types are captured automatically without code
        changes.

        Args:
            event_type: The raw event type string.
            data: The event data dictionary.
        """
        metadata = {"event_type": event_type}
        self.history.append_message(
            session_id=self.session_id,
            role=MessageRole.EVENT,
            content=json.dumps(data),
            metadata=metadata
        )

    def finalize_assistant_response(self, metadata: dict | None = None) -> None:
        """Finalize and save the accumulated assistant response.

        Args:
            metadata: Optional metadata to include with the message.
        """
        if self._text_parts:
            self.history.append_message(
                session_id=self.session_id,
                role=MessageRole.ASSISTANT,
                content="".join(self._text_parts),
                metadata=metadata
            )
            self._text_parts = []

    def process_event(self, event_type: str, data: dict) -> None:
        """Process an event and update history accordingly.

        This is a convenience method that routes events to the appropriate
        handler based on event type.  Unrecognized events are persisted as
        generic event records so that new SDK message types are captured
        automatically. Control/protocol events (session_id, ready, compact_*,
        cancel_request) are intentionally excluded from history.

        Args:
            event_type: The type of event (from EventType constants).
            data: The event data dictionary.
        """
        if event_type == EventType.TEXT_DELTA:
            self.accumulate_text(data.get("text", ""))
        elif event_type == EventType.TOOL_USE:
            self.save_tool_use(data)
        elif event_type == EventType.TOOL_RESULT:
            self.save_tool_result(data)
        elif event_type == EventType.USER_ANSWER:
            self.save_user_answer(data)
        elif event_type == EventType.DONE:
            self.finalize_assistant_response()
            self.save_result_message(data)
        elif event_type == EventType.CANCELLED:
            # Finalize any partial response with cancelled metadata
            self.finalize_assistant_response(metadata={"cancelled": True})
        elif event_type == EventType.ERROR:
            self.history.append_message(
                session_id=self.session_id,
                role=MessageRole.SYSTEM,
                content=str(data.get("error", data.get("message", json.dumps(data)))),
                metadata={"event_type": "error"}
            )
        elif event_type not in _CONTROL_EVENT_TYPES:
            # Catch-all: persist any unrecognized event for future analysis
            self.save_generic_event(event_type, data)
