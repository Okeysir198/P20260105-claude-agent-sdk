"""Comprehensive tests for message_utils.py.

Tests cover:
- All output format variations (sse, ws)
- All message types (SystemMessage, StreamEvent, AssistantMessage, ResultMessage, UserMessage)
- Edge cases (None content, empty content, different content types)
- All branch paths

Note: Uses unittest.mock.MagicMock with spec to properly simulate SDK types.
"""
from unittest.mock import MagicMock

import pytest

from api.constants import EventType
from api.services.message_utils import (
    _format_event,
    _normalize_tool_result_content,
    _convert_system_message,
    _convert_stream_event,
    _convert_tool_use_block,
    _convert_tool_result_block,
    _convert_assistant_message,
    _convert_result_message,
    _convert_user_message,
    convert_messages,
    convert_message,
    convert_message_to_sse,
    message_to_dict,
    message_to_dicts,
    convert_messages_to_sse,
)


# ============================================================================
# Fixtures for creating mock message objects
# ============================================================================

def create_mock_system_message(subtype="init", data=None):
    """Create a mock SystemMessage that passes isinstance and type() checks."""
    from claude_agent_sdk.types import SystemMessage
    return SystemMessage(subtype=subtype, data=data or {})


def create_mock_stream_event(delta_type="text_delta", text=None, tool_use_id=None, content=None, is_error=False):
    """Create a mock StreamEvent that passes isinstance and type() checks."""
    from claude_agent_sdk.types import StreamEvent
    delta = {"type": delta_type}
    if text is not None:
        delta["text"] = text
    if tool_use_id is not None:
        delta["tool_use_id"] = tool_use_id
    if content is not None:
        delta["content"] = content
    if is_error:
        delta["is_error"] = is_error
    return StreamEvent(
        uuid="test-uuid",
        session_id="test-session",
        event={"delta": delta}
    )


def create_mock_tool_use_block(block_id="tool-123", name="bash", input_data=None):
    """Create a mock ToolUseBlock that passes isinstance and type() checks."""
    from claude_agent_sdk.types import ToolUseBlock
    return ToolUseBlock(id=block_id, name=name, input=input_data or {})


def create_mock_tool_result_block(tool_use_id="tool-123", content="output", is_error=False):
    """Create a mock ToolResultBlock that passes isinstance and type() checks."""
    from claude_agent_sdk.types import ToolResultBlock
    return ToolResultBlock(tool_use_id=tool_use_id, content=content, is_error=is_error)


def create_mock_assistant_message(content=None):
    """Create a mock AssistantMessage that passes isinstance and type() checks."""
    from claude_agent_sdk.types import AssistantMessage
    return AssistantMessage(
        content=content or [],
        model="test-model"
    )


def create_mock_user_message(content=None):
    """Create a mock UserMessage that passes isinstance and type() checks."""
    from claude_agent_sdk.types import UserMessage
    return UserMessage(content=content or [])


def create_mock_result_message(num_turns=1, total_cost_usd=0.0):
    """Create a mock ResultMessage that passes isinstance and type() checks."""
    from claude_agent_sdk.types import ResultMessage
    return ResultMessage(
        subtype="result",
        duration_ms=0,
        duration_api_ms=0,
        is_error=False,
        num_turns=num_turns,
        session_id="test-session",
        total_cost_usd=total_cost_usd
    )


# ============================================================================
# Tests for _format_event
# ============================================================================

class TestFormatEvent:
    """Tests for _format_event function."""

    def test_format_event_sse(self):
        """Test formatting event for SSE output."""
        result = _format_event("test_event", {"key": "value"}, "sse")
        assert result == {"event": "test_event", "data": '{"key": "value"}'}

    def test_format_event_ws(self):
        """Test formatting event for WebSocket output."""
        result = _format_event("test_event", {"key": "value"}, "ws")
        assert result == {"type": "test_event", "key": "value"}

    def test_format_event_sse_with_complex_data(self):
        """Test SSE formatting with nested data."""
        data = {"nested": {"key": "value"}, "list": [1, 2, 3]}
        result = _format_event("complex", data, "sse")
        assert result["event"] == "complex"
        assert '"nested":' in result["data"]
        assert '"list":' in result["data"]

    def test_format_event_ws_with_complex_data(self):
        """Test WS formatting with nested data."""
        data = {"nested": {"key": "value"}, "list": [1, 2, 3]}
        result = _format_event("complex", data, "ws")
        assert result["type"] == "complex"
        assert result["nested"] == {"key": "value"}
        assert result["list"] == [1, 2, 3]


# ============================================================================
# Tests for _normalize_tool_result_content
# ============================================================================

class TestNormalizeToolResultContent:
    """Tests for _normalize_tool_result_content function."""

    def test_normalize_none(self):
        """Test normalizing None content."""
        result = _normalize_tool_result_content(None)
        assert result == ""

    def test_normalize_string(self):
        """Test normalizing string content."""
        result = _normalize_tool_result_content("test string")
        assert result == "test string"

    def test_normalize_list_of_strings(self):
        """Test normalizing list of strings."""
        result = _normalize_tool_result_content(["line1", "line2", "line3"])
        assert result == "line1\nline2\nline3"

    def test_normalize_list_of_numbers(self):
        """Test normalizing list of numbers."""
        result = _normalize_tool_result_content([1, 2, 3])
        assert result == "1\n2\n3"

    def test_normalize_list_of_mixed_types(self):
        """Test normalizing list of mixed types."""
        result = _normalize_tool_result_content(["text", 123, True])
        assert result == "text\n123\nTrue"

    def test_normalize_empty_list(self):
        """Test normalizing empty list."""
        result = _normalize_tool_result_content([])
        assert result == ""

    def test_normalize_integer(self):
        """Test normalizing integer content."""
        result = _normalize_tool_result_content(42)
        assert result == "42"

    def test_normalize_float(self):
        """Test normalizing float content."""
        result = _normalize_tool_result_content(3.14)
        assert result == "3.14"

    def test_normalize_boolean(self):
        """Test normalizing boolean content."""
        result = _normalize_tool_result_content(True)
        assert result == "True"

    def test_normalize_dict(self):
        """Test normalizing dict content."""
        result = _normalize_tool_result_content({"key": "value"})
        assert result == "{'key': 'value'}"


# ============================================================================
# Tests for _convert_system_message
# ============================================================================

class TestConvertSystemMessage:
    """Tests for _convert_system_message function."""

    def test_convert_system_message_init_with_session_id_sse(self):
        """Test converting SystemMessage with init subtype and session_id (SSE)."""
        msg = create_mock_system_message(subtype="init", data={"session_id": "test-session-123"})

        result = _convert_system_message(msg, "sse")

        assert result is not None
        assert result["event"] == EventType.SESSION_ID
        assert result["data"] == '{"session_id": "test-session-123"}'

    def test_convert_system_message_init_with_session_id_ws(self):
        """Test converting SystemMessage with init subtype and session_id (WS)."""
        msg = create_mock_system_message(subtype="init", data={"session_id": "test-session-456"})

        result = _convert_system_message(msg, "ws")

        assert result is not None
        assert result["type"] == EventType.SESSION_ID
        assert result["session_id"] == "test-session-456"

    def test_convert_system_message_non_init_subtype(self):
        """Test converting SystemMessage with non-init subtype."""
        msg = create_mock_system_message(subtype="other", data={"session_id": "test-session"})

        result = _convert_system_message(msg, "sse")

        assert result is None

    def test_convert_system_message_no_data_attribute(self):
        """Test converting SystemMessage without data attribute."""
        from claude_agent_sdk.types import SystemMessage
        msg = MagicMock(spec=SystemMessage)
        msg.subtype = "init"
        # Simulate missing data attribute
        del msg.data

        result = _convert_system_message(msg, "sse")

        assert result is None

    def test_convert_system_message_empty_session_id(self):
        """Test converting SystemMessage with empty session_id."""
        msg = create_mock_system_message(subtype="init", data={"session_id": ""})

        result = _convert_system_message(msg, "sse")

        assert result is None

    def test_convert_system_message_missing_session_id(self):
        """Test converting SystemMessage without session_id in data."""
        msg = create_mock_system_message(subtype="init", data={"other_key": "other_value"})

        result = _convert_system_message(msg, "ws")

        assert result is None


# ============================================================================
# Tests for _convert_stream_event
# ============================================================================

class TestConvertStreamEvent:
    """Tests for _convert_stream_event function."""

    def test_convert_stream_event_text_delta_sse(self):
        """Test converting StreamEvent with text_delta (SSE)."""
        msg = create_mock_stream_event(delta_type="text_delta", text="Hello")

        result = _convert_stream_event(msg, "sse")

        assert result is not None
        assert result["event"] == EventType.TEXT_DELTA
        assert result["data"] == '{"text": "Hello"}'

    def test_convert_stream_event_text_delta_ws(self):
        """Test converting StreamEvent with text_delta (WS)."""
        msg = create_mock_stream_event(delta_type="text_delta", text="World")

        result = _convert_stream_event(msg, "ws")

        assert result is not None
        assert result["type"] == EventType.TEXT_DELTA
        assert result["text"] == "World"

    def test_convert_stream_event_text_delta_empty_text(self):
        """Test converting StreamEvent with empty text_delta."""
        msg = create_mock_stream_event(delta_type="text_delta", text="")

        result = _convert_stream_event(msg, "sse")

        assert result is not None
        assert result["data"] == '{"text": ""}'

    def test_convert_stream_event_text_delta_missing_text(self):
        """Test converting StreamEvent with missing text field."""
        msg = create_mock_stream_event(delta_type="text_delta")

        result = _convert_stream_event(msg, "ws")

        assert result is not None
        assert result["text"] == ""

    def test_convert_stream_event_tool_result_sse(self):
        """Test converting StreamEvent with tool_result (SSE)."""
        msg = create_mock_stream_event(
            delta_type="tool_result",
            tool_use_id="tool-123",
            content="output",
            is_error=False
        )

        result = _convert_stream_event(msg, "sse")

        assert result is not None
        assert result["event"] == EventType.TOOL_RESULT
        assert "tool_use_id" in result["data"]
        assert "tool-123" in result["data"]

    def test_convert_stream_event_tool_result_ws(self):
        """Test converting StreamEvent with tool_result (WS)."""
        msg = create_mock_stream_event(
            delta_type="tool_result",
            tool_use_id="tool-456",
            content="output",
            is_error=True
        )

        result = _convert_stream_event(msg, "ws")

        assert result is not None
        assert result["type"] == EventType.TOOL_RESULT
        assert result["tool_use_id"] == "tool-456"
        assert result["content"] == "output"
        assert result["is_error"] is True

    def test_convert_stream_event_tool_result_with_list_content(self):
        """Test converting StreamEvent with list content."""
        msg = create_mock_stream_event(
            delta_type="tool_result",
            tool_use_id="tool-789",
            content=["line1", "line2"]
        )

        result = _convert_stream_event(msg, "ws")

        assert result["content"] == "line1\nline2"

    def test_convert_stream_event_tool_result_with_none_content(self):
        """Test converting StreamEvent with None content."""
        msg = create_mock_stream_event(
            delta_type="tool_result",
            tool_use_id="tool-000",
            content=None
        )

        result = _convert_stream_event(msg, "ws")

        assert result["content"] == ""

    def test_convert_stream_event_unknown_delta_type(self):
        """Test converting StreamEvent with unknown delta type."""
        msg = create_mock_stream_event(delta_type="unknown_type")

        result = _convert_stream_event(msg, "sse")

        assert result is None

    def test_convert_stream_event_empty_event(self):
        """Test converting StreamEvent with empty event."""
        from claude_agent_sdk.types import StreamEvent
        msg = MagicMock(spec=StreamEvent)
        msg.event = {}

        result = _convert_stream_event(msg, "sse")

        assert result is None

    def test_convert_stream_event_no_delta(self):
        """Test converting StreamEvent without delta key."""
        from claude_agent_sdk.types import StreamEvent
        msg = MagicMock(spec=StreamEvent)
        msg.event = {"other_key": "value"}

        result = _convert_stream_event(msg, "ws")

        assert result is None


# ============================================================================
# Tests for _convert_tool_use_block
# ============================================================================

class TestConvertToolUseBlock:
    """Tests for _convert_tool_use_block function."""

    def test_convert_tool_use_block_sse(self):
        """Test converting ToolUseBlock (SSE)."""
        block = create_mock_tool_use_block(
            block_id="tool-use-123",
            name="bash",
            input_data={"command": "ls -la"}
        )

        result = _convert_tool_use_block(block, "sse")

        assert result["event"] == EventType.TOOL_USE
        assert '"id": "tool-use-123"' in result["data"]
        assert '"name": "bash"' in result["data"]

    def test_convert_tool_use_block_ws(self):
        """Test converting ToolUseBlock (WS)."""
        block = create_mock_tool_use_block(
            block_id="tool-use-456",
            name="read",
            input_data={"file_path": "/tmp/file.txt"}
        )

        result = _convert_tool_use_block(block, "ws")

        assert result["type"] == EventType.TOOL_USE
        assert result["id"] == "tool-use-456"
        assert result["name"] == "read"
        assert result["input"] == {"file_path": "/tmp/file.txt"}

    def test_convert_tool_use_block_with_none_input(self):
        """Test converting ToolUseBlock with None input."""
        block = create_mock_tool_use_block(
            block_id="tool-use-789",
            name="test",
            input_data=None
        )

        result = _convert_tool_use_block(block, "ws")

        assert result["input"] == {}


# ============================================================================
# Tests for _convert_tool_result_block
# ============================================================================

class TestConvertToolResultBlock:
    """Tests for _convert_tool_result_block function."""

    def test_convert_tool_result_block_sse(self):
        """Test converting ToolResultBlock (SSE)."""
        block = create_mock_tool_result_block(
            tool_use_id="tool-use-123",
            content="tool output",
            is_error=False
        )

        result = _convert_tool_result_block(block, "sse")

        assert result["event"] == EventType.TOOL_RESULT
        assert "tool_use_id" in result["data"]
        assert "tool-use-123" in result["data"]

    def test_convert_tool_result_block_ws(self):
        """Test converting ToolResultBlock (WS)."""
        block = create_mock_tool_result_block(
            tool_use_id="tool-use-456",
            content="tool output",
            is_error=True
        )

        result = _convert_tool_result_block(block, "ws")

        assert result["type"] == EventType.TOOL_RESULT
        assert result["tool_use_id"] == "tool-use-456"
        assert result["content"] == "tool output"
        assert result["is_error"] is True

    def test_convert_tool_result_block_with_list_content(self):
        """Test converting ToolResultBlock with list content."""
        block = create_mock_tool_result_block(
            tool_use_id="tool-789",
            content=["line1", "line2", "line3"]
        )

        result = _convert_tool_result_block(block, "ws")

        assert result["content"] == "line1\nline2\nline3"

    def test_convert_tool_result_block_with_none_content(self):
        """Test converting ToolResultBlock with None content."""
        block = create_mock_tool_result_block(
            tool_use_id="tool-000",
            content=None
        )

        result = _convert_tool_result_block(block, "ws")

        assert result["content"] == ""

    def test_convert_tool_result_block_without_is_error_attribute(self):
        """Test converting ToolResultBlock without is_error attribute."""
        from claude_agent_sdk.types import ToolResultBlock
        block = MagicMock(spec=ToolResultBlock)
        block.tool_use_id = "tool-111"
        block.content = "output"
        # Remove is_error attribute
        del block.is_error

        result = _convert_tool_result_block(block, "ws")

        assert result["is_error"] is False


# ============================================================================
# Tests for _convert_assistant_message
# ============================================================================

class TestConvertAssistantMessage:
    """Tests for _convert_assistant_message function."""

    def test_convert_assistant_message_with_tool_use_sse(self):
        """Test converting AssistantMessage with ToolUseBlock (SSE)."""
        block = create_mock_tool_use_block(
            block_id="tool-123",
            name="bash",
            input_data={"cmd": "ls"}
        )

        msg = create_mock_assistant_message(content=[block])

        result = _convert_assistant_message(msg, "sse")

        assert result is not None
        assert result["event"] == EventType.TOOL_USE

    def test_convert_assistant_message_with_tool_use_ws(self):
        """Test converting AssistantMessage with ToolUseBlock (WS)."""
        block = create_mock_tool_use_block(
            block_id="tool-456",
            name="read",
            input_data={"path": "/tmp"}
        )

        msg = create_mock_assistant_message(content=[block])

        result = _convert_assistant_message(msg, "ws")

        assert result is not None
        assert result["type"] == EventType.TOOL_USE
        assert result["id"] == "tool-456"

    def test_convert_assistant_message_with_tool_result_sse(self):
        """Test converting AssistantMessage with ToolResultBlock (SSE)."""
        block = create_mock_tool_result_block(
            tool_use_id="tool-789",
            content="output",
            is_error=False
        )

        msg = create_mock_assistant_message(content=[block])

        result = _convert_assistant_message(msg, "sse")

        assert result is not None
        assert result["event"] == EventType.TOOL_RESULT

    def test_convert_assistant_message_with_tool_result_ws(self):
        """Test converting AssistantMessage with ToolResultBlock (WS)."""
        block = create_mock_tool_result_block(
            tool_use_id="tool-999",
            content="error output",
            is_error=True
        )

        msg = create_mock_assistant_message(content=[block])

        result = _convert_assistant_message(msg, "ws")

        assert result is not None
        assert result["type"] == EventType.TOOL_RESULT
        assert result["content"] == "error output"
        assert result["is_error"] is True

    def test_convert_assistant_message_with_mixed_blocks(self):
        """Test converting AssistantMessage with mixed block types."""
        tool_use_block = create_mock_tool_use_block(
            block_id="tool-123",
            name="bash",
            input_data={}
        )

        tool_result_block = create_mock_tool_result_block(
            tool_use_id="tool-456",
            content="output",
            is_error=False
        )

        msg = create_mock_assistant_message(content=[tool_use_block, tool_result_block])

        result = _convert_assistant_message(msg, "ws")

        # Should return first matching block (tool_use)
        assert result["type"] == EventType.TOOL_USE
        assert result["id"] == "tool-123"

    def test_convert_assistant_message_empty_content(self):
        """Test converting AssistantMessage with empty content."""
        msg = create_mock_assistant_message(content=[])

        result = _convert_assistant_message(msg, "sse")

        assert result is None


# ============================================================================
# Tests for _convert_result_message
# ============================================================================

class TestConvertResultMessage:
    """Tests for _convert_result_message function."""

    def test_convert_result_message_sse(self):
        """Test converting ResultMessage (SSE)."""
        msg = create_mock_result_message(num_turns=5, total_cost_usd=0.0125)

        result = _convert_result_message(msg, "sse")

        assert result["event"] == EventType.DONE
        assert '"turn_count": 5' in result["data"]
        assert '"total_cost_usd": 0.0125' in result["data"]

    def test_convert_result_message_ws(self):
        """Test converting ResultMessage (WS)."""
        msg = create_mock_result_message(num_turns=10, total_cost_usd=0.0250)

        result = _convert_result_message(msg, "ws")

        assert result["type"] == EventType.DONE
        assert result["turn_count"] == 10
        assert result["total_cost_usd"] == 0.0250

    def test_convert_result_message_with_none_cost(self):
        """Test converting ResultMessage with None cost."""
        msg = create_mock_result_message(num_turns=3, total_cost_usd=None)

        result = _convert_result_message(msg, "ws")

        assert result["turn_count"] == 3
        assert result["total_cost_usd"] == 0.0

    def test_convert_result_message_zero_turns(self):
        """Test converting ResultMessage with zero turns."""
        msg = create_mock_result_message(num_turns=0, total_cost_usd=0.0)

        result = _convert_result_message(msg, "sse")

        assert '"turn_count": 0' in result["data"]


# ============================================================================
# Tests for _convert_user_message
# ============================================================================

class TestConvertUserMessage:
    """Tests for _convert_user_message function."""

    def test_convert_user_message_single_tool_result_sse(self):
        """Test converting UserMessage with single tool_result (SSE)."""
        block = create_mock_tool_result_block(
            tool_use_id="tool-123",
            content="output",
            is_error=False
        )

        msg = create_mock_user_message(content=[block])

        result = _convert_user_message(msg, "sse")

        assert len(result) == 1
        assert result[0]["event"] == EventType.TOOL_RESULT

    def test_convert_user_message_single_tool_result_ws(self):
        """Test converting UserMessage with single tool_result (WS)."""
        block = create_mock_tool_result_block(
            tool_use_id="tool-456",
            content="output",
            is_error=True
        )

        msg = create_mock_user_message(content=[block])

        result = _convert_user_message(msg, "ws")

        assert len(result) == 1
        assert result[0]["type"] == EventType.TOOL_RESULT
        assert result[0]["tool_use_id"] == "tool-456"

    def test_convert_user_message_multiple_tool_results(self):
        """Test converting UserMessage with multiple tool_results."""
        block1 = create_mock_tool_result_block(
            tool_use_id="tool-1",
            content="output1",
            is_error=False
        )

        block2 = create_mock_tool_result_block(
            tool_use_id="tool-2",
            content="output2",
            is_error=False
        )

        msg = create_mock_user_message(content=[block1, block2])

        result = _convert_user_message(msg, "ws")

        assert len(result) == 2
        assert result[0]["tool_use_id"] == "tool-1"
        assert result[1]["tool_use_id"] == "tool-2"

    def test_convert_user_message_empty_content(self):
        """Test converting UserMessage with empty content."""
        msg = create_mock_user_message(content=[])

        result = _convert_user_message(msg, "sse")

        assert result == []


# ============================================================================
# Tests for convert_messages
# ============================================================================

class TestConvertMessages:
    """Tests for convert_messages generator function."""

    def test_convert_messages_user_message(self):
        """Test convert_messages with UserMessage."""
        block = create_mock_tool_result_block(
            tool_use_id="tool-123",
            content="output",
            is_error=False
        )

        msg = create_mock_user_message(content=[block])

        results = list(convert_messages(msg, "ws"))

        assert len(results) == 1
        assert results[0]["type"] == EventType.TOOL_RESULT

    def test_convert_messages_user_message_multiple_blocks(self):
        """Test convert_messages with UserMessage containing multiple blocks."""
        block1 = create_mock_tool_result_block(
            tool_use_id="tool-1",
            content="out1",
            is_error=False
        )

        block2 = create_mock_tool_result_block(
            tool_use_id="tool-2",
            content="out2",
            is_error=False
        )

        msg = create_mock_user_message(content=[block1, block2])

        results = list(convert_messages(msg, "sse"))

        assert len(results) == 2

    def test_convert_messages_system_message(self):
        """Test convert_messages with SystemMessage."""
        msg = create_mock_system_message(
            subtype="init",
            data={"session_id": "sess-123"}
        )

        results = list(convert_messages(msg, "ws"))

        assert len(results) == 1
        assert results[0]["type"] == EventType.SESSION_ID

    def test_convert_messages_stream_event_text_delta(self):
        """Test convert_messages with StreamEvent text_delta."""
        msg = create_mock_stream_event(
            delta_type="text_delta",
            text="Hello"
        )

        results = list(convert_messages(msg, "sse"))

        assert len(results) == 1
        assert results[0]["event"] == EventType.TEXT_DELTA

    def test_convert_messages_stream_event_tool_result(self):
        """Test convert_messages with StreamEvent tool_result."""
        msg = create_mock_stream_event(
            delta_type="tool_result",
            tool_use_id="tool-123",
            content="output"
        )

        results = list(convert_messages(msg, "ws"))

        assert len(results) == 1
        assert results[0]["type"] == EventType.TOOL_RESULT

    def test_convert_messages_assistant_message_tool_use(self):
        """Test convert_messages with AssistantMessage tool_use."""
        block = create_mock_tool_use_block(
            block_id="tool-456",
            name="bash",
            input_data={}
        )

        msg = create_mock_assistant_message(content=[block])

        results = list(convert_messages(msg, "sse"))

        assert len(results) == 1
        assert results[0]["event"] == EventType.TOOL_USE

    def test_convert_messages_result_message(self):
        """Test convert_messages with ResultMessage."""
        msg = create_mock_result_message(num_turns=5, total_cost_usd=0.01)

        results = list(convert_messages(msg, "ws"))

        assert len(results) == 1
        assert results[0]["type"] == EventType.DONE

    def test_convert_messages_system_message_no_session_id(self):
        """Test convert_messages with SystemMessage without session_id."""
        msg = create_mock_system_message(
            subtype="other",
            data={}
        )

        results = list(convert_messages(msg, "ws"))

        assert results == []

    def test_convert_messages_stream_event_unknown_type(self):
        """Test convert_messages with StreamEvent unknown delta."""
        msg = create_mock_stream_event(delta_type="unknown")

        results = list(convert_messages(msg, "sse"))

        assert results == []

    def test_convert_messages_assistant_message_no_tool_blocks(self):
        """Test convert_messages with AssistantMessage without tool blocks."""
        msg = create_mock_assistant_message(content=[])

        results = list(convert_messages(msg, "ws"))

        assert results == []

    def test_convert_messages_default_output_format(self):
        """Test convert_messages with default output format (sse)."""
        msg = create_mock_result_message(num_turns=1, total_cost_usd=0.001)

        results = list(convert_messages(msg))

        assert len(results) == 1
        assert "event" in results[0]
        assert "data" in results[0]


# ============================================================================
# Tests for convert_message
# ============================================================================

class TestConvertMessage:
    """Tests for convert_message function."""

    def test_convert_message_user_message_returns_none(self):
        """Test convert_message with UserMessage returns None."""
        msg = create_mock_user_message()

        result = convert_message(msg, "ws")

        assert result is None

    def test_convert_message_system_message_sse(self):
        """Test convert_message with SystemMessage (SSE)."""
        msg = create_mock_system_message(
            subtype="init",
            data={"session_id": "sess-123"}
        )

        result = convert_message(msg, "sse")

        assert result is not None
        assert result["event"] == EventType.SESSION_ID

    def test_convert_message_system_message_ws(self):
        """Test convert_message with SystemMessage (WS)."""
        msg = create_mock_system_message(
            subtype="init",
            data={"session_id": "sess-456"}
        )

        result = convert_message(msg, "ws")

        assert result is not None
        assert result["type"] == EventType.SESSION_ID

    def test_convert_message_stream_event(self):
        """Test convert_message with StreamEvent."""
        msg = create_mock_stream_event(
            delta_type="text_delta",
            text="Hi"
        )

        result = convert_message(msg, "sse")

        assert result is not None
        assert result["event"] == EventType.TEXT_DELTA

    def test_convert_message_assistant_message(self):
        """Test convert_message with AssistantMessage."""
        block = create_mock_tool_use_block(
            block_id="tool-789",
            name="bash",
            input_data={}
        )

        msg = create_mock_assistant_message(content=[block])

        result = convert_message(msg, "ws")

        assert result is not None
        assert result["type"] == EventType.TOOL_USE

    def test_convert_message_result_message(self):
        """Test convert_message with ResultMessage."""
        msg = create_mock_result_message(num_turns=3, total_cost_usd=0.005)

        result = convert_message(msg, "sse")

        assert result is not None
        assert result["event"] == EventType.DONE

    def test_convert_message_system_message_invalid_returns_none(self):
        """Test convert_message with invalid SystemMessage returns None."""
        msg = create_mock_system_message(
            subtype="other",
            data={}
        )

        result = convert_message(msg, "sse")

        assert result is None

    def test_convert_message_default_output_format(self):
        """Test convert_message with default output format (sse)."""
        msg = create_mock_result_message(num_turns=1, total_cost_usd=0.001)

        result = convert_message(msg)

        assert result is not None
        assert "event" in result
        assert "data" in result


# ============================================================================
# Tests for convert_message_to_sse
# ============================================================================

class TestConvertMessageToSse:
    """Tests for convert_message_to_sse function."""

    def test_convert_message_to_sse_system_message(self):
        """Test convert_message_to_sse with SystemMessage."""
        msg = create_mock_system_message(
            subtype="init",
            data={"session_id": "sess-sse"}
        )

        result = convert_message_to_sse(msg)

        assert result is not None
        assert result["event"] == EventType.SESSION_ID
        assert "data" in result

    def test_convert_message_to_sse_user_message(self):
        """Test convert_message_to_sse with UserMessage."""
        msg = create_mock_user_message()

        result = convert_message_to_sse(msg)

        assert result is None

    def test_convert_message_to_sse_result_message(self):
        """Test convert_message_to_sse with ResultMessage."""
        msg = create_mock_result_message(num_turns=2, total_cost_usd=0.002)

        result = convert_message_to_sse(msg)

        assert result["event"] == EventType.DONE


# ============================================================================
# Tests for message_to_dict
# ============================================================================

class TestMessageToDict:
    """Tests for message_to_dict function."""

    def test_message_to_dict_system_message(self):
        """Test message_to_dict with SystemMessage."""
        msg = create_mock_system_message(
            subtype="init",
            data={"session_id": "sess-dict"}
        )

        result = message_to_dict(msg)

        assert result is not None
        assert result["type"] == EventType.SESSION_ID
        assert result["session_id"] == "sess-dict"

    def test_message_to_dict_user_message(self):
        """Test message_to_dict with UserMessage returns None."""
        msg = create_mock_user_message()

        result = message_to_dict(msg)

        assert result is None

    def test_message_to_dict_stream_event(self):
        """Test message_to_dict with StreamEvent."""
        msg = create_mock_stream_event(
            delta_type="text_delta",
            text="test"
        )

        result = message_to_dict(msg)

        assert result is not None
        assert result["type"] == EventType.TEXT_DELTA
        assert result["text"] == "test"

    def test_message_to_dict_result_message(self):
        """Test message_to_dict with ResultMessage."""
        msg = create_mock_result_message(num_turns=7, total_cost_usd=0.007)

        result = message_to_dict(msg)

        assert result["type"] == EventType.DONE
        assert result["turn_count"] == 7
        assert result["total_cost_usd"] == 0.007


# ============================================================================
# Tests for message_to_dicts
# ============================================================================

class TestMessageToDicts:
    """Tests for message_to_dicts function."""

    def test_message_to_dicts_user_message_single_block(self):
        """Test message_to_dicts with UserMessage single block."""
        block = create_mock_tool_result_block(
            tool_use_id="tool-dicts-1",
            content="output",
            is_error=False
        )

        msg = create_mock_user_message(content=[block])

        results = message_to_dicts(msg)

        assert len(results) == 1
        assert results[0]["type"] == EventType.TOOL_RESULT
        assert results[0]["tool_use_id"] == "tool-dicts-1"

    def test_message_to_dicts_user_message_multiple_blocks(self):
        """Test message_to_dicts with UserMessage multiple blocks."""
        block1 = create_mock_tool_result_block(
            tool_use_id="tool-dicts-2",
            content="out1",
            is_error=False
        )

        block2 = create_mock_tool_result_block(
            tool_use_id="tool-dicts-3",
            content="out2",
            is_error=False
        )

        msg = create_mock_user_message(content=[block1, block2])

        results = message_to_dicts(msg)

        assert len(results) == 2
        assert results[0]["tool_use_id"] == "tool-dicts-2"
        assert results[1]["tool_use_id"] == "tool-dicts-3"

    def test_message_to_dicts_system_message(self):
        """Test message_to_dicts with SystemMessage."""
        msg = create_mock_system_message(
            subtype="init",
            data={"session_id": "sess-dicts-multi"}
        )

        results = message_to_dicts(msg)

        assert len(results) == 1
        assert results[0]["type"] == EventType.SESSION_ID

    def test_message_to_dicts_stream_event(self):
        """Test message_to_dicts with StreamEvent."""
        msg = create_mock_stream_event(
            delta_type="text_delta",
            text="text"
        )

        results = message_to_dicts(msg)

        assert len(results) == 1
        assert results[0]["type"] == EventType.TEXT_DELTA

    def test_message_to_dicts_result_message(self):
        """Test message_to_dicts with ResultMessage."""
        msg = create_mock_result_message(num_turns=4, total_cost_usd=0.004)

        results = message_to_dicts(msg)

        assert len(results) == 1
        assert results[0]["type"] == EventType.DONE


# ============================================================================
# Tests for convert_messages_to_sse
# ============================================================================

class TestConvertMessagesToSse:
    """Tests for convert_messages_to_sse function."""

    def test_convert_messages_to_sse_user_message(self):
        """Test convert_messages_to_sse with UserMessage."""
        block = create_mock_tool_result_block(
            tool_use_id="tool-sse-1",
            content="output",
            is_error=False
        )

        msg = create_mock_user_message(content=[block])

        results = convert_messages_to_sse(msg)

        assert len(results) == 1
        assert results[0]["event"] == EventType.TOOL_RESULT

    def test_convert_messages_to_sse_user_message_multiple(self):
        """Test convert_messages_to_sse with UserMessage multiple blocks."""
        block1 = create_mock_tool_result_block(
            tool_use_id="tool-sse-2",
            content="out1",
            is_error=False
        )

        block2 = create_mock_tool_result_block(
            tool_use_id="tool-sse-3",
            content="out2",
            is_error=False
        )

        msg = create_mock_user_message(content=[block1, block2])

        results = convert_messages_to_sse(msg)

        assert len(results) == 2

    def test_convert_messages_to_sse_system_message(self):
        """Test convert_messages_to_sse with SystemMessage."""
        msg = create_mock_system_message(
            subtype="init",
            data={"session_id": "sess-sse-multi"}
        )

        results = convert_messages_to_sse(msg)

        assert len(results) == 1
        assert results[0]["event"] == EventType.SESSION_ID

    def test_convert_messages_to_sse_stream_event(self):
        """Test convert_messages_to_sse with StreamEvent."""
        msg = create_mock_stream_event(
            delta_type="text_delta",
            text="delta"
        )

        results = convert_messages_to_sse(msg)

        assert len(results) == 1
        assert results[0]["event"] == EventType.TEXT_DELTA

    def test_convert_messages_to_sse_result_message(self):
        """Test convert_messages_to_sse with ResultMessage."""
        msg = create_mock_result_message(num_turns=6, total_cost_usd=0.006)

        results = convert_messages_to_sse(msg)

        assert len(results) == 1
        assert results[0]["event"] == EventType.DONE
