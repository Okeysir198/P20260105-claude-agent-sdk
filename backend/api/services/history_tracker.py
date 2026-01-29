"""Centralized history tracking for conversation events.

This module provides a HistoryTracker class that handles all history-related
operations during conversation streaming, including accumulating text deltas,
saving tool events, and finalizing assistant responses.
"""
import json
from dataclasses import dataclass, field

from agent.core.storage import HistoryStorage
from api.constants import EventType, MessageRole


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

    def save_user_message(self, content: str) -> None:
        """Save a user message to history.

        Args:
            content: The user's message content.
        """
        self.history.append_message(
            session_id=self.session_id,
            role=MessageRole.USER,
            content=content
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
        self.history.append_message(
            session_id=self.session_id,
            role=MessageRole.TOOL_USE,
            content=json.dumps(data.get("input", {})),
            tool_name=data.get("tool_name") or data.get("name"),
            tool_use_id=data.get("tool_use_id") or data.get("id")
        )

    def save_tool_result(self, data: dict) -> None:
        """Save a tool result event to history.

        Args:
            data: Tool result data containing tool_use_id, content, and is_error.
        """
        self.history.append_message(
            session_id=self.session_id,
            role=MessageRole.TOOL_RESULT,
            content=str(data.get("content", "")),
            tool_use_id=data.get("tool_use_id"),
            is_error=data.get("is_error", False)
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
        handler based on event type.

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
        elif event_type == EventType.CANCELLED:
            # Finalize any partial response with cancelled metadata
            self.finalize_assistant_response(metadata={"cancelled": True})
