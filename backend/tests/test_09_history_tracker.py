"""Tests for HistoryTracker message ordering, completeness, and metadata.

Verifies fixes for:
1. Assistant text saved in correct order (before tool_use)
2. Multi-turn text interleaving preserved
3. Text-only messages finalized properly
4. No empty assistant entries for tool-only messages
5. ThinkingBlock saved with correct metadata
6. Model metadata captured on assistant text and tool_use entries
7. AssistantMessage.error captured as system message
8. UserMessage TextBlock saved alongside ToolResultBlock
9. process_event() flushes text before TOOL_USE
10. Trailing text after last tool call saved on finalize
"""
from dataclasses import dataclass
from typing import Any

import pytest

from api.services.history_tracker import HistoryTracker
from api.constants import EventType, MessageRole


# ---------------------------------------------------------------------------
# Minimal SDK type stubs (avoid importing real SDK in unit tests)
# ---------------------------------------------------------------------------

@dataclass
class _TextBlock:
    text: str
    type: str = "text"


@dataclass
class _ToolUseBlock:
    id: str
    name: str
    input: dict
    type: str = "tool_use"


@dataclass
class _ToolResultBlock:
    tool_use_id: str
    content: str
    is_error: bool = False
    type: str = "tool_result"


@dataclass
class _ThinkingBlock:
    thinking: str
    signature: str = ""


@dataclass
class _AssistantMessage:
    content: list
    model: str = "claude-sonnet-4-5-20250929"
    parent_tool_use_id: str | None = None
    error: str | None = None


@dataclass
class _UserMessage:
    content: str | list
    uuid: str | None = None
    parent_tool_use_id: str | None = None


# ---------------------------------------------------------------------------
# Fake HistoryStorage that records append_message calls in order
# ---------------------------------------------------------------------------

class FakeHistoryStorage:
    """In-memory history storage that records all appended messages."""

    def __init__(self):
        self.messages: list[dict[str, Any]] = []

    def append_message(self, **kwargs) -> None:
        self.messages.append(kwargs)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def storage():
    return FakeHistoryStorage()


@pytest.fixture
def tracker(storage):
    return HistoryTracker(session_id="test-session", history=storage)


# ---------------------------------------------------------------------------
# Monkey-patch isinstance checks so our stubs pass the SDK type guards.
# We patch the module-level references that HistoryTracker uses.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _patch_sdk_types(monkeypatch):
    """Patch SDK type references in history_tracker module to use our stubs."""
    import api.services.history_tracker as ht_mod

    monkeypatch.setattr(ht_mod, "TextBlock", _TextBlock)
    monkeypatch.setattr(ht_mod, "ToolUseBlock", _ToolUseBlock)
    monkeypatch.setattr(ht_mod, "ToolResultBlock", _ToolResultBlock)
    monkeypatch.setattr(ht_mod, "ThinkingBlock", _ThinkingBlock)
    monkeypatch.setattr(ht_mod, "AssistantMessage", _AssistantMessage)
    monkeypatch.setattr(ht_mod, "UserMessage", _UserMessage)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def roles(storage: FakeHistoryStorage) -> list[str]:
    """Return list of roles from stored messages in order."""
    return [m["role"] for m in storage.messages]


# ===========================================================================
# Tests
# ===========================================================================


class TestTextBeforeToolUse:
    """Test 1: Text appears before tool_use in history (single turn)."""

    def test_text_then_tool_use_order(self, tracker, storage):
        msg = _AssistantMessage(content=[
            _TextBlock(text="I'll read the file."),
            _ToolUseBlock(id="tu1", name="Read", input={"path": "/a.txt"}),
        ])
        tracker.save_from_assistant_message(msg)

        assert len(storage.messages) == 2
        assert storage.messages[0]["role"] == MessageRole.ASSISTANT
        assert storage.messages[0]["content"] == "I'll read the file."
        assert storage.messages[1]["role"] == MessageRole.TOOL_USE
        assert storage.messages[1]["tool_name"] == "Read"


class TestMultiTurnInterleaving:
    """Test 2: Multi-turn text interleaving preserved correctly."""

    def test_multiple_text_tool_pairs(self, tracker, storage):
        msg = _AssistantMessage(content=[
            _TextBlock(text="Reading file A."),
            _ToolUseBlock(id="tu1", name="Read", input={"path": "a.txt"}),
            _TextBlock(text="Now editing file B."),
            _ToolUseBlock(id="tu2", name="Edit", input={"path": "b.txt"}),
        ])
        tracker.save_from_assistant_message(msg)

        assert len(storage.messages) == 4
        assert roles(storage) == [
            MessageRole.ASSISTANT,
            MessageRole.TOOL_USE,
            MessageRole.ASSISTANT,
            MessageRole.TOOL_USE,
        ]
        assert storage.messages[0]["content"] == "Reading file A."
        assert storage.messages[1]["tool_name"] == "Read"
        assert storage.messages[2]["content"] == "Now editing file B."
        assert storage.messages[3]["tool_name"] == "Edit"


class TestTextOnlyFinalize:
    """Test 3: Text-only messages finalized properly."""

    def test_text_only_message_saved_on_finalize(self, tracker, storage):
        msg = _AssistantMessage(content=[
            _TextBlock(text="Here is the answer."),
        ])
        tracker.save_from_assistant_message(msg)

        # Text is buffered in _canonical_text_parts, not yet flushed
        assert len(storage.messages) == 0

        # Finalize should flush it
        tracker.finalize_assistant_response()
        assert len(storage.messages) == 1
        assert storage.messages[0]["role"] == MessageRole.ASSISTANT
        assert storage.messages[0]["content"] == "Here is the answer."


class TestNoEmptyAssistantEntry:
    """Test 4: No empty assistant entries for tool-only messages."""

    def test_tool_only_no_empty_text(self, tracker, storage):
        msg = _AssistantMessage(content=[
            _ToolUseBlock(id="tu1", name="Bash", input={"command": "ls"}),
        ])
        tracker.save_from_assistant_message(msg)

        assert len(storage.messages) == 1
        assert storage.messages[0]["role"] == MessageRole.TOOL_USE
        # No assistant text entry


class TestThinkingBlockSaved:
    """Test 5: ThinkingBlock saved with correct metadata."""

    def test_thinking_block_metadata(self, tracker, storage):
        msg = _AssistantMessage(
            content=[
                _ThinkingBlock(thinking="Let me think about this..."),
            ],
            model="claude-opus-4-6",
        )
        tracker.save_from_assistant_message(msg)

        assert len(storage.messages) == 1
        m = storage.messages[0]
        assert m["role"] == MessageRole.ASSISTANT
        assert m["content"] == "Let me think about this..."
        assert m["metadata"]["block_type"] == "thinking"
        assert m["metadata"]["model"] == "claude-opus-4-6"


class TestModelMetadata:
    """Test 6: Model metadata captured on assistant text and tool_use entries."""

    def test_model_on_text_and_tool_use(self, tracker, storage):
        msg = _AssistantMessage(
            content=[
                _TextBlock(text="Working on it."),
                _ToolUseBlock(id="tu1", name="Read", input={"path": "x.py"}),
            ],
            model="claude-sonnet-4-5-20250929",
        )
        tracker.save_from_assistant_message(msg)

        # Text entry should have model in metadata
        text_msg = storage.messages[0]
        assert text_msg["role"] == MessageRole.ASSISTANT
        assert text_msg["metadata"]["model"] == "claude-sonnet-4-5-20250929"

        # Tool use entry should have model in metadata
        tool_msg = storage.messages[1]
        assert tool_msg["role"] == MessageRole.TOOL_USE
        assert tool_msg["metadata"]["model"] == "claude-sonnet-4-5-20250929"


class TestAssistantMessageError:
    """Test 7: AssistantMessage.error captured as system message."""

    def test_error_saved_as_system(self, tracker, storage):
        msg = _AssistantMessage(
            content=[_TextBlock(text="Something went wrong.")],
            error="rate_limit",
        )
        tracker.save_from_assistant_message(msg)

        # Error should be saved immediately (text is still buffered)
        assert len(storage.messages) == 1
        m = storage.messages[0]
        assert m["role"] == MessageRole.SYSTEM
        assert m["content"] == "rate_limit"
        assert m["metadata"]["event_type"] == "assistant_error"

    def test_no_error_when_none(self, tracker, storage):
        msg = _AssistantMessage(
            content=[_TextBlock(text="All good.")],
            error=None,
        )
        tracker.save_from_assistant_message(msg)

        # Only buffered text, no system error message
        assert len(storage.messages) == 0


class TestUserMessageTextBlock:
    """Test 8: UserMessage TextBlock saved alongside ToolResultBlock."""

    def test_user_text_and_tool_result(self, tracker, storage):
        msg = _UserMessage(content=[
            _ToolResultBlock(tool_use_id="tu1", content="file contents here"),
            _TextBlock(text="Here is the context."),
        ])
        tracker.save_from_user_message(msg)

        assert len(storage.messages) == 2
        # Iteration order matches content list order
        result_msg = storage.messages[0]
        assert result_msg["role"] == MessageRole.TOOL_RESULT

        text_msg = storage.messages[1]
        assert text_msg["role"] == MessageRole.USER
        assert text_msg["content"] == "Here is the context."

    def test_user_text_block_only(self, tracker, storage):
        msg = _UserMessage(content=[
            _TextBlock(text="Just some user text."),
        ])
        tracker.save_from_user_message(msg)

        assert len(storage.messages) == 1
        assert storage.messages[0]["role"] == MessageRole.USER
        assert storage.messages[0]["content"] == "Just some user text."

    def test_user_string_content_skipped(self, tracker, storage):
        msg = _UserMessage(content="plain string content")
        tracker.save_from_user_message(msg)

        # String content is skipped by save_from_user_message
        assert len(storage.messages) == 0

    def test_user_empty_text_block_skipped(self, tracker, storage):
        msg = _UserMessage(content=[
            _TextBlock(text="   "),
        ])
        tracker.save_from_user_message(msg)

        assert len(storage.messages) == 0


class TestProcessEventFlush:
    """Test 9: process_event() flushes text before TOOL_USE."""

    def test_text_delta_then_tool_use_via_process_event(self, tracker, storage):
        tracker.process_event(EventType.TEXT_DELTA, {"text": "Let me "})
        tracker.process_event(EventType.TEXT_DELTA, {"text": "check."})
        tracker.process_event(EventType.TOOL_USE, {
            "tool_name": "Read",
            "id": "tu1",
            "input": {"path": "/f.txt"},
        })

        assert len(storage.messages) == 2
        assert storage.messages[0]["role"] == MessageRole.ASSISTANT
        assert storage.messages[0]["content"] == "Let me check."
        assert storage.messages[1]["role"] == MessageRole.TOOL_USE

    def test_no_flush_without_text(self, tracker, storage):
        """TOOL_USE without preceding text should not create empty assistant entry."""
        tracker.process_event(EventType.TOOL_USE, {
            "tool_name": "Bash",
            "id": "tu1",
            "input": {"command": "ls"},
        })

        assert len(storage.messages) == 1
        assert storage.messages[0]["role"] == MessageRole.TOOL_USE


class TestTrailingTextOnFinalize:
    """Test 10: Trailing text after last tool call saved on finalize."""

    def test_trailing_text_flushed(self, tracker, storage):
        msg = _AssistantMessage(content=[
            _TextBlock(text="First text."),
            _ToolUseBlock(id="tu1", name="Read", input={"path": "x.txt"}),
            _TextBlock(text="Done reading."),
        ])
        tracker.save_from_assistant_message(msg)

        # "First text." flushed before tool_use, tool_use saved
        assert len(storage.messages) == 2
        assert storage.messages[0]["content"] == "First text."
        assert storage.messages[1]["role"] == MessageRole.TOOL_USE

        # "Done reading." is still buffered in _canonical_text_parts
        tracker.finalize_assistant_response()

        assert len(storage.messages) == 3
        assert storage.messages[2]["role"] == MessageRole.ASSISTANT
        assert storage.messages[2]["content"] == "Done reading."


class TestThinkingBeforeToolUse:
    """ThinkingBlock interleaved with text and tool use maintains order."""

    def test_thinking_text_tool_order(self, tracker, storage):
        msg = _AssistantMessage(
            content=[
                _ThinkingBlock(thinking="Hmm, I need to think."),
                _TextBlock(text="Let me read that file."),
                _ToolUseBlock(id="tu1", name="Read", input={"path": "a.txt"}),
            ],
            model="claude-opus-4-6",
        )
        tracker.save_from_assistant_message(msg)

        assert len(storage.messages) == 3
        assert roles(storage) == [
            MessageRole.ASSISTANT,  # thinking
            MessageRole.ASSISTANT,  # text (flushed before tool)
            MessageRole.TOOL_USE,
        ]
        assert storage.messages[0]["metadata"]["block_type"] == "thinking"
        assert storage.messages[1]["content"] == "Let me read that file."


class TestProcessEventDone:
    """process_event with DONE finalizes text and saves result."""

    def test_done_finalizes_and_saves_result(self, tracker, storage):
        tracker.process_event(EventType.TEXT_DELTA, {"text": "Final answer."})
        tracker.process_event(EventType.DONE, {"cost_usd": 0.01, "num_turns": 1})

        assert len(storage.messages) == 2
        assert storage.messages[0]["role"] == MessageRole.ASSISTANT
        assert storage.messages[0]["content"] == "Final answer."
        assert storage.messages[1]["role"] == MessageRole.SYSTEM
        assert storage.messages[1]["metadata"]["event_type"] == "result"
