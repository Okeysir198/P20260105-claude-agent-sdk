"""Tests for HistoryTracker service."""
import json
from unittest.mock import MagicMock

import pytest

from api.constants import EventType, MessageRole
from api.services.history_tracker import HistoryTracker


class TestHistoryTracker:
    """Test cases for HistoryTracker."""

    def test_save_user_message(self):
        """Test saving a user message to history."""
        mock_history = MagicMock()
        tracker = HistoryTracker(session_id="test-session", history=mock_history)

        tracker.save_user_message("Hello, world!")

        mock_history.append_message.assert_called_once_with(
            session_id="test-session",
            role=MessageRole.USER,
            content="Hello, world!"
        )

    def test_accumulate_text(self):
        """Test text accumulation."""
        mock_history = MagicMock()
        tracker = HistoryTracker(session_id="test-session", history=mock_history)

        tracker.accumulate_text("Hello, ")
        tracker.accumulate_text("world!")

        assert tracker.get_accumulated_text() == "Hello, world!"

    def test_get_accumulated_text(self):
        """Test getting accumulated text without clearing."""
        mock_history = MagicMock()
        tracker = HistoryTracker(session_id="test-session", history=mock_history)

        tracker.accumulate_text("Test text")
        text = tracker.get_accumulated_text()

        assert text == "Test text"
        # Text should still be there
        assert tracker.get_accumulated_text() == "Test text"

    def test_has_accumulated_text(self):
        """Test checking if text has been accumulated."""
        mock_history = MagicMock()
        tracker = HistoryTracker(session_id="test-session", history=mock_history)

        assert not tracker.has_accumulated_text()

        tracker.accumulate_text("Some text")
        assert tracker.has_accumulated_text()

    def test_save_tool_use(self):
        """Test saving tool use event."""
        mock_history = MagicMock()
        tracker = HistoryTracker(session_id="test-session", history=mock_history)

        tool_data = {
            "tool_name": "bash",
            "tool_use_id": "tool_123",
            "input": {"command": "ls -la"}
        }

        tracker.save_tool_use(tool_data)

        mock_history.append_message.assert_called_once_with(
            session_id="test-session",
            role=MessageRole.TOOL_USE,
            content=json.dumps({"command": "ls -la"}),
            tool_name="bash",
            tool_use_id="tool_123"
        )

    def test_save_tool_use_with_id_field(self):
        """Test saving tool use with 'id' field instead of 'tool_use_id'."""
        mock_history = MagicMock()
        tracker = HistoryTracker(session_id="test-session", history=mock_history)

        tool_data = {
            "name": "read",
            "id": "tool_456",
            "input": {"file_path": "/path/to/file"}
        }

        tracker.save_tool_use(tool_data)

        mock_history.append_message.assert_called_once_with(
            session_id="test-session",
            role=MessageRole.TOOL_USE,
            content=json.dumps({"file_path": "/path/to/file"}),
            tool_name="read",
            tool_use_id="tool_456"
        )

    def test_save_tool_result(self):
        """Test saving tool result event."""
        mock_history = MagicMock()
        tracker = HistoryTracker(session_id="test-session", history=mock_history)

        result_data = {
            "tool_use_id": "tool_123",
            "content": "Output from tool",
            "is_error": False
        }

        tracker.save_tool_result(result_data)

        mock_history.append_message.assert_called_once_with(
            session_id="test-session",
            role=MessageRole.TOOL_RESULT,
            content="Output from tool",
            tool_use_id="tool_123",
            is_error=False
        )

    def test_save_tool_result_with_error(self):
        """Test saving tool result with error flag."""
        mock_history = MagicMock()
        tracker = HistoryTracker(session_id="test-session", history=mock_history)

        result_data = {
            "tool_use_id": "tool_123",
            "content": "Error occurred",
            "is_error": True
        }

        tracker.save_tool_result(result_data)

        mock_history.append_message.assert_called_once_with(
            session_id="test-session",
            role=MessageRole.TOOL_RESULT,
            content="Error occurred",
            tool_use_id="tool_123",
            is_error=True
        )

    def test_save_tool_result_default_is_error(self):
        """Test saving tool result without is_error defaults to False."""
        mock_history = MagicMock()
        tracker = HistoryTracker(session_id="test-session", history=mock_history)

        result_data = {
            "tool_use_id": "tool_123",
            "content": "Tool output"
        }

        tracker.save_tool_result(result_data)

        mock_history.append_message.assert_called_once_with(
            session_id="test-session",
            role=MessageRole.TOOL_RESULT,
            content="Tool output",
            tool_use_id="tool_123",
            is_error=False
        )

    def test_save_user_answer(self):
        """Test saving user answer as tool_result."""
        mock_history = MagicMock()
        tracker = HistoryTracker(session_id="test-session", history=mock_history)

        answer_data = {
            "question_id": "q_123",
            "answers": {"choice": "option_a", "reason": "because"}
        }

        tracker.save_user_answer(answer_data)

        mock_history.append_message.assert_called_once_with(
            session_id="test-session",
            role=MessageRole.TOOL_RESULT,
            content=json.dumps({"choice": "option_a", "reason": "because"}),
            tool_use_id="q_123",
            is_error=False
        )

    def test_finalize_assistant_response_with_text(self):
        """Test finalizing assistant response with accumulated text."""
        mock_history = MagicMock()
        tracker = HistoryTracker(session_id="test-session", history=mock_history)

        tracker.accumulate_text("Hello")
        tracker.accumulate_text(", ")
        tracker.accumulate_text("world!")

        metadata = {"cost": 0.001, "turn_count": 1}
        tracker.finalize_assistant_response(metadata)

        mock_history.append_message.assert_called_once_with(
            session_id="test-session",
            role=MessageRole.ASSISTANT,
            content="Hello, world!",
            metadata=metadata
        )

    def test_finalize_assistant_response_without_text(self):
        """Test finalizing when no text accumulated."""
        mock_history = MagicMock()
        tracker = HistoryTracker(session_id="test-session", history=mock_history)

        tracker.finalize_assistant_response()

        mock_history.append_message.assert_not_called()

    def test_finalize_clears_accumulated_text(self):
        """Test that finalizing clears accumulated text."""
        mock_history = MagicMock()
        tracker = HistoryTracker(session_id="test-session", history=mock_history)

        tracker.accumulate_text("Some text")
        tracker.finalize_assistant_response()

        assert not tracker.has_accumulated_text()
        assert tracker.get_accumulated_text() == ""

    def test_process_event_text_delta(self):
        """Test processing text_delta event."""
        mock_history = MagicMock()
        tracker = HistoryTracker(session_id="test-session", history=mock_history)

        tracker.process_event(EventType.TEXT_DELTA, {"text": "Hello"})

        assert tracker.get_accumulated_text() == "Hello"

    def test_process_event_tool_use(self):
        """Test processing tool_use event."""
        mock_history = MagicMock()
        tracker = HistoryTracker(session_id="test-session", history=mock_history)

        tracker.process_event(EventType.TOOL_USE, {
            "tool_name": "bash",
            "tool_use_id": "tool_123",
            "input": {"command": "echo test"}
        })

        mock_history.append_message.assert_called_once()

    def test_process_event_tool_result(self):
        """Test processing tool_result event."""
        mock_history = MagicMock()
        tracker = HistoryTracker(session_id="test-session", history=mock_history)

        tracker.process_event(EventType.TOOL_RESULT, {
            "tool_use_id": "tool_123",
            "content": "done",
            "is_error": False
        })

        mock_history.append_message.assert_called_once()

    def test_process_event_user_answer(self):
        """Test processing user_answer event."""
        mock_history = MagicMock()
        tracker = HistoryTracker(session_id="test-session", history=mock_history)

        tracker.process_event(EventType.USER_ANSWER, {
            "question_id": "q_123",
            "answers": {"choice": "yes"}
        })

        mock_history.append_message.assert_called_once()

    def test_process_event_done(self):
        """Test processing done event."""
        mock_history = MagicMock()
        tracker = HistoryTracker(session_id="test-session", history=mock_history)

        tracker.accumulate_text("Final text")
        tracker.process_event(EventType.DONE, {})

        mock_history.append_message.assert_called_once_with(
            session_id="test-session",
            role=MessageRole.ASSISTANT,
            content="Final text",
            metadata=None
        )

    def test_process_event_unknown_type(self):
        """Test processing unknown event type does nothing."""
        mock_history = MagicMock()
        tracker = HistoryTracker(session_id="test-session", history=mock_history)

        tracker.process_event("unknown_event", {"data": "value"})

        mock_history.append_message.assert_not_called()
