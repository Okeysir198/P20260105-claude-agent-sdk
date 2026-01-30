"""Test suite for streaming input functionality.

Tests async generator message input:
- create_message_generator with different content types
- StreamingInputHandler message queuing
- FIFO order preservation
- Basic error handling
"""
import pytest

from api.services.streaming_input import (
    create_message_generator,
    StreamingInputHandler
)


class TestCreateMessageGenerator:
    """Test create_message_generator function with various input types."""

    @pytest.mark.asyncio
    async def test_string_input(self):
        """Generator should handle plain string input correctly."""
        content = "Hello, world!"
        session_id = "test-session-123"

        messages = []
        async for msg in create_message_generator(content, session_id):
            messages.append(msg)

        assert len(messages) == 1
        assert messages[0]["type"] == "user"
        assert messages[0]["message"]["role"] == "user"
        assert messages[0]["session_id"] == session_id

        # Content should be normalized to list of dicts (JSON-serializable)
        content_list = messages[0]["message"]["content"]
        assert len(content_list) == 1
        assert isinstance(content_list[0], dict)
        assert content_list[0]["text"] == content

    @pytest.mark.asyncio
    async def test_multipart_text_input(self):
        """Generator should handle multi-part text content."""
        content = [
            {"type": "text", "text": "First message"},
            {"type": "text", "text": "Second message"}
        ]
        session_id = "test-session-456"

        messages = []
        async for msg in create_message_generator(content, session_id):
            messages.append(msg)

        assert len(messages) == 1
        content_list = messages[0]["message"]["content"]
        assert len(content_list) == 2
        assert content_list[0]["text"] == "First message"
        assert content_list[1]["text"] == "Second message"

    @pytest.mark.asyncio
    async def test_multipart_with_image(self):
        """Generator should handle multi-part content with images."""
        content = [
            {"type": "text", "text": "Analyze this:"},
            {
                "type": "image",
                "source": {
                    "type": "url",
                    "url": "https://example.com/image.jpg"
                }
            }
        ]
        session_id = "test-session-789"

        messages = []
        async for msg in create_message_generator(content, session_id):
            messages.append(msg)

        assert len(messages) == 1
        content_list = messages[0]["message"]["content"]
        assert len(content_list) == 2
        assert content_list[0]["type"] == "text"
        assert content_list[1]["type"] == "image"


class TestStreamingInputHandler:
    """Test StreamingInputHandler class for queued message support."""

    @pytest.mark.asyncio
    async def test_add_and_generate_message(self):
        """Handler should add message and generate it correctly."""
        handler = StreamingInputHandler("session-xyz")

        await handler.add_message("Hello, queue!")

        assert handler.has_pending_messages() is True

        # Generate and verify message
        messages = []
        async for msg in handler.generate_messages():
            messages.append(msg)
            handler.complete()  # Stop after first message

        assert len(messages) == 1
        assert messages[0]["message"]["content"][0]["text"] == "Hello, queue!"

    @pytest.mark.asyncio
    async def test_add_multipart_message(self):
        """Handler should add multi-part messages to queue."""
        handler = StreamingInputHandler("session-xyz")

        content = [
            {"type": "text", "text": "Queued message 1"},
            {"type": "text", "text": "Queued message 2"}
        ]
        await handler.add_message(content)

        messages = []
        async for msg in handler.generate_messages():
            messages.append(msg)
            handler.complete()

        assert len(messages) == 1
        assert len(messages[0]["message"]["content"]) == 2

    @pytest.mark.asyncio
    async def test_multiple_messages_fifo_order(self):
        """Handler should process messages in FIFO order."""
        handler = StreamingInputHandler("session-fifo")

        # Add multiple messages
        await handler.add_message("First")
        await handler.add_message("Second")
        await handler.add_message("Third")
        handler.complete()

        messages = []
        async for msg in handler.generate_messages():
            messages.append(msg)

        assert len(messages) == 3
        assert messages[0]["message"]["content"][0]["text"] == "First"
        assert messages[1]["message"]["content"][0]["text"] == "Second"
        assert messages[2]["message"]["content"][0]["text"] == "Third"

    @pytest.mark.asyncio
    async def test_add_message_with_parent_tool_use_id(self):
        """Handler should preserve parent_tool_use_id in queued messages."""
        handler = StreamingInputHandler("session-xyz")

        await handler.add_message("Tool response", parent_tool_use_id="tool-abc")

        messages = []
        async for msg in handler.generate_messages():
            messages.append(msg)
            handler.complete()

        assert len(messages) == 1
        assert messages[0]["parent_tool_use_id"] == "tool-abc"

    @pytest.mark.asyncio
    async def test_mixed_content_types_in_queue(self):
        """Handler should queue messages with different content types."""
        handler = StreamingInputHandler("session-mixed")

        # String message
        await handler.add_message("String message")

        # Multi-part text
        await handler.add_message([
            {"type": "text", "text": "Multi-part 1"},
            {"type": "text", "text": "Multi-part 2"}
        ])

        # Multi-part with image
        await handler.add_message([
            {"type": "text", "text": "With image"},
            {"type": "image", "source": {"type": "url", "url": "https://example.com/img.jpg"}}
        ])

        handler.complete()

        messages = []
        async for msg in handler.generate_messages():
            messages.append(msg)

        assert len(messages) == 3
        assert len(messages[0]["message"]["content"]) == 1
        assert len(messages[1]["message"]["content"]) == 2
        assert len(messages[2]["message"]["content"]) == 2
        assert messages[2]["message"]["content"][1]["type"] == "image"


class TestErrorHandling:
    """Test error handling in streaming input."""

    @pytest.mark.asyncio
    async def test_error_handling_invalid_content(self):
        """Generator should raise ValueError for invalid content."""
        session_id = "test-session-error"

        # Invalid content type
        with pytest.raises(ValueError, match="Invalid content format"):
            async for _ in create_message_generator(12345, session_id):
                pass

    @pytest.mark.asyncio
    async def test_handler_invalid_content_in_add(self):
        """add_message should raise ValueError for invalid content."""
        handler = StreamingInputHandler("session-error")

        with pytest.raises(ValueError, match="Failed to add message"):
            await handler.add_message(12345)
