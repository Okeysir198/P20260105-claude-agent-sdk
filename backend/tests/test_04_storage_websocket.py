"""Test suite for storage and WebSocket integration.

Tests core multi-part content persistence:
- Save/load string and multi-part messages
- Mixed format sessions (backward compatibility)
- HistoryTracker integration
"""
import json
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from agent.core.storage import HistoryStorage, serialize_content, deserialize_content
from api.services.history_tracker import HistoryTracker
from api.services.content_normalizer import ContentBlock


class TestContentSerialization:
    """Test content serialization and deserialization."""

    def test_serialize_string(self):
        """String content should remain unchanged."""
        content = "Hello, world!"
        serialized = serialize_content(content)
        assert serialized == content
        assert isinstance(serialized, str)

    def test_serialize_multipart(self):
        """List of dicts should remain unchanged."""
        content = [
            {"type": "text", "text": "First"},
            {"type": "text", "text": "Second"}
        ]
        serialized = serialize_content(content)
        assert serialized == content
        assert isinstance(serialized, list)

    def test_serialize_content_blocks(self):
        """Pydantic ContentBlock objects should convert to dicts."""
        blocks = [
            ContentBlock(type="text", text="Hello"),
            ContentBlock(type="text", text="World")
        ]
        serialized = serialize_content(blocks)

        assert isinstance(serialized, list)
        assert len(serialized) == 2
        assert serialized[0] == {"type": "text", "text": "Hello", "source": None}

    def test_deserialize_string(self):
        """String content should remain string after deserialization."""
        content = "Hello, world!"
        deserialized = deserialize_content(content)
        assert deserialized == content
        assert isinstance(deserialized, str)

    def test_deserialize_list(self):
        """List content should remain list after deserialization."""
        content = [{"type": "text", "text": "Hi"}]
        deserialized = deserialize_content(content)
        assert deserialized == content
        assert isinstance(deserialized, list)


class TestHistoryStorage:
    """Test HistoryStorage with multi-part content support."""

    def test_save_and_load_string(self):
        """Storage should save and load string messages correctly."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            storage = HistoryStorage(data_dir=temp_dir)

            storage.append_message(
                session_id="test-session",
                role="user",
                content="Hello, world!"
            )

            messages = storage.get_messages("test-session")
            assert len(messages) == 1
            assert messages[0].role == "user"
            assert messages[0].content == "Hello, world!"
            assert isinstance(messages[0].content, str)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_save_and_load_multipart_text(self):
        """Storage should save and load multi-part text messages correctly."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            storage = HistoryStorage(data_dir=temp_dir)

            content = [
                {"type": "text", "text": "First message"},
                {"type": "text", "text": "Second message"}
            ]
            storage.append_message(
                session_id="test-session",
                role="user",
                content=content
            )

            messages = storage.get_messages("test-session")
            assert len(messages) == 1
            assert isinstance(messages[0].content, list)
            assert len(messages[0].content) == 2
            assert messages[0].content[0]["text"] == "First message"
            assert messages[0].content[1]["text"] == "Second message"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_save_and_load_multipart_with_image(self):
        """Storage should save and load multi-part messages with images correctly."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            storage = HistoryStorage(data_dir=temp_dir)

            content = [
                {"type": "text", "text": "Analyze this:"},
                {
                    "type": "image",
                    "source": {
                        "type": "url",
                        "url": "https://example.com/img.jpg"
                    }
                }
            ]
            storage.append_message(
                session_id="test-session",
                role="user",
                content=content
            )

            messages = storage.get_messages("test-session")
            assert len(messages) == 1
            assert isinstance(messages[0].content, list)
            assert len(messages[0].content) == 2
            assert messages[0].content[0]["type"] == "text"
            assert messages[0].content[1]["type"] == "image"
            assert messages[0].content[1]["source"]["url"] == "https://example.com/img.jpg"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_mixed_format_session(self):
        """Session should support both string and multi-part messages."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            storage = HistoryStorage(data_dir=temp_dir)
            session_id = "test-session-mixed"

            # Add string message
            storage.append_message(
                session_id=session_id,
                role="user",
                content="String message"
            )

            # Add multi-part message
            storage.append_message(
                session_id=session_id,
                role="assistant",
                content=[
                    {"type": "text", "text": "Response"},
                    {"type": "image", "source": {"type": "url", "url": "https://example.com/img.jpg"}}
                ]
            )

            # Add another string message
            storage.append_message(
                session_id=session_id,
                role="user",
                content="Another string message"
            )

            messages = storage.get_messages(session_id)

            assert len(messages) == 3
            assert isinstance(messages[0].content, str)
            assert isinstance(messages[1].content, list)
            assert isinstance(messages[2].content, str)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestHistoryTracker:
    """Test HistoryTracker with multi-part content support."""

    def test_save_user_message_string(self):
        """HistoryTracker should save string content correctly."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            storage = HistoryStorage(data_dir=temp_dir)
            tracker = HistoryTracker(session_id="test-session", history=storage)

            tracker.save_user_message("Hello, world!")

            messages = storage.get_messages("test-session")
            assert len(messages) == 1
            assert messages[0].content == "Hello, world!"
            assert isinstance(messages[0].content, str)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_save_user_message_multipart_text(self):
        """HistoryTracker should save multi-part text content correctly."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            storage = HistoryStorage(data_dir=temp_dir)
            tracker = HistoryTracker(session_id="test-session", history=storage)

            content = [
                {"type": "text", "text": "First message"},
                {"type": "text", "text": "Second message"}
            ]
            tracker.save_user_message(content)

            messages = storage.get_messages("test-session")
            assert len(messages) == 1
            assert isinstance(messages[0].content, list)
            assert len(messages[0].content) == 2
            assert messages[0].content[0]["text"] == "First message"
            assert messages[0].content[1]["text"] == "Second message"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_save_user_message_multipart_with_image(self):
        """HistoryTracker should save multi-part content with images correctly."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            storage = HistoryStorage(data_dir=temp_dir)
            tracker = HistoryTracker(session_id="test-session", history=storage)

            content = [
                {"type": "text", "text": "Analyze this:"},
                {"type": "image", "source": {"type": "url", "url": "https://example.com/img.jpg"}}
            ]
            tracker.save_user_message(content)

            messages = storage.get_messages("test-session")
            assert len(messages) == 1
            assert isinstance(messages[0].content, list)
            assert len(messages[0].content) == 2
            assert messages[0].content[0]["type"] == "text"
            assert messages[0].content[1]["type"] == "image"
            assert messages[0].content[1]["source"]["url"] == "https://example.com/img.jpg"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
