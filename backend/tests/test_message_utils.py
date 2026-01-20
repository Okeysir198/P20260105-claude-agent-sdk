"""Tests for message conversion utilities."""
import json

from claude_agent_sdk.types import (
    SystemMessage,
    StreamEvent,
    AssistantMessage,
    UserMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

from api.services.message_utils import convert_message_to_sse


def test_system_message_init():
    """Test SystemMessage with init subtype emits session_id event."""
    msg = SystemMessage(
        subtype="init",
        data={"session_id": "test-session-123"}
    )
    result = convert_message_to_sse(msg)

    assert result is not None
    assert result["event"] == "session_id"
    data = json.loads(result["data"])
    assert data["session_id"] == "test-session-123"


def test_system_message_other_subtype():
    """Test SystemMessage with other subtypes returns None."""
    msg = SystemMessage(
        subtype="other",
        data={"key": "value"}
    )
    result = convert_message_to_sse(msg)

    assert result is None


def test_stream_event_text_delta():
    """Test StreamEvent with text_delta emits text_delta event."""
    msg = StreamEvent(event={
        "delta": {
            "type": "text_delta",
            "text": "Hello, world!"
        }
    })
    result = convert_message_to_sse(msg)

    assert result is not None
    assert result["event"] == "text_delta"
    data = json.loads(result["data"])
    assert data["text"] == "Hello, world!"


def test_stream_event_empty_text():
    """Test StreamEvent with empty text delta."""
    msg = StreamEvent(event={
        "delta": {
            "type": "text_delta",
            "text": ""
        }
    })
    result = convert_message_to_sse(msg)

    assert result is not None
    assert result["event"] == "text_delta"
    data = json.loads(result["data"])
    assert data["text"] == ""


def test_stream_event_other_delta_type():
    """Test StreamEvent with non-text delta returns None."""
    msg = StreamEvent(event={
        "delta": {
            "type": "other_delta",
            "data": "value"
        }
    })
    result = convert_message_to_sse(msg)

    assert result is None


def test_assistant_message_tool_use():
    """Test AssistantMessage with tool_use emits tool_use event."""
    msg = AssistantMessage(content=[
        ToolUseBlock(
            id="tool-123",
            name="search",
            input={"query": "test"}
        )
    ])
    result = convert_message_to_sse(msg)

    assert result is not None
    assert result["event"] == "tool_use"
    data = json.loads(result["data"])
    assert data["id"] == "tool-123"
    assert data["name"] == "search"
    assert data["input"] == {"query": "test"}


def test_assistant_message_text_only():
    """Test AssistantMessage with only text blocks returns None."""
    msg = AssistantMessage(content=[
        TextBlock(text="Hello, world!")
    ])
    result = convert_message_to_sse(msg)

    # Text blocks are handled by StreamEvent in streaming mode
    assert result is None


def test_assistant_message_mixed_content():
    """Test AssistantMessage with mixed content returns tool_use."""
    msg = AssistantMessage(content=[
        TextBlock(text="Let me search that for you."),
        ToolUseBlock(
            id="tool-456",
            name="calculator",
            input={"expression": "2+2"}
        ),
        TextBlock(text="Done!")
    ])
    result = convert_message_to_sse(msg)

    # Should return tool_use event for first tool block
    assert result is not None
    assert result["event"] == "tool_use"
    data = json.loads(result["data"])
    assert data["name"] == "calculator"


def test_user_message():
    """Test UserMessage returns None (not streamed)."""
    msg = UserMessage(content=[
        TextBlock(text="Hello, assistant!")
    ])
    result = convert_message_to_sse(msg)

    assert result is None


def test_result_message():
    """Test ResultMessage emits done event with stats."""
    msg = ResultMessage(
        subtype="success",
        num_turns=5,
        total_cost_usd=0.012345
    )
    result = convert_message_to_sse(msg)

    assert result is not None
    assert result["event"] == "done"
    data = json.loads(result["data"])
    assert data["turn_count"] == 5
    assert data["total_cost_usd"] == 0.012345


def test_result_message_zero_cost():
    """Test ResultMessage with zero cost."""
    msg = ResultMessage(
        subtype="success",
        num_turns=1,
        total_cost_usd=0.0
    )
    result = convert_message_to_sse(msg)

    assert result is not None
    assert result["event"] == "done"
    data = json.loads(result["data"])
    assert data["turn_count"] == 1
    assert data["total_cost_usd"] == 0.0


def test_result_message_none_cost():
    """Test ResultMessage with None cost defaults to 0.0."""
    msg = ResultMessage(
        subtype="success",
        num_turns=3,
        total_cost_usd=None
    )
    result = convert_message_to_sse(msg)

    assert result is not None
    data = json.loads(result["data"])
    assert data["total_cost_usd"] == 0.0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
