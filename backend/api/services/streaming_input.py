"""Async generator wrapper for streaming input mode.

This module provides utilities for converting user content into the async generator
format expected by the Claude Agent SDK's streaming input mode.

The SDK's streaming mode allows dynamic message sending during a conversation,
enabling interactive workflows where messages can be queued and sent sequentially.
"""
import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

from api.services.content_normalizer import normalize_content

logger = logging.getLogger(__name__)


async def create_message_generator(
    content: str | list,
    session_id: str,
    parent_tool_use_id: str | None = None
) -> AsyncGenerator[dict[str, Any], None]:
    """Create an async generator that yields normalized message dictionaries.

    This function converts user content into the format expected by the SDK's
    streaming input mode. It handles both simple string content and multi-part
    content (lists with text, images, etc.).

    Args:
        content: The user message content as a string or list of content blocks.
        session_id: The session identifier for the conversation.
        parent_tool_use_id: Optional tool use ID if this is a tool response.

    Yields:
        Message dictionaries in SDK format:
        {
            "type": "user",
            "message": {"role": "user", "content": <normalized_content>},
            "parent_tool_use_id": <tool_use_id or None>,
            "session_id": <session_id>
        }

    Examples:
        >>> # Simple string content
        >>> async for msg in create_message_generator("Hello", "session-123"):
        ...     await transport.write(json.dumps(msg) + "\\n")

        >>> # Multi-part content (text + images)
        >>> content = [{"type": "text", "text": "Analyze this"}, {"type": "image", ...}]
        >>> async for msg in create_message_generator(content, "session-123"):
        ...     await transport.write(json.dumps(msg) + "\\n")
    """
    try:
        # Normalize content to SDK-expected format
        normalized_content = await asyncio.to_thread(
            normalize_content, content
        )

        # Convert ContentBlock objects to dicts for JSON serialization
        content_dicts = [block.model_dump() for block in normalized_content]

        # Yield single message in SDK format
        yield {
            "type": "user",
            "message": {
                "role": "user",
                "content": content_dicts
            },
            "parent_tool_use_id": parent_tool_use_id,
            "session_id": session_id
        }

    except Exception as e:
        logger.error(f"Error creating message generator: {e}", exc_info=True)
        raise ValueError(f"Invalid content format: {e}") from e


class StreamingInputHandler:
    """Manages streaming input with queued message support.

    This handler provides a queue-based interface for dynamically adding
    messages to a streaming conversation. Messages added to the queue are
    yielded sequentially, enabling interactive workflows where user input
    arrives incrementally.

    Use cases:
    - Chat interfaces with follow-up questions
    - Tool callbacks that require user input
    - Interactive debugging sessions
    - Multi-turn conversations with dynamic message injection

    Attributes:
        session_id: The session identifier for all messages.
        message_queue: Async queue holding pending messages.

    Examples:
        >>> handler = StreamingInputHandler("session-123")
        >>> async for msg in handler.generate_messages():
        ...     await transport.write(json.dumps(msg) + "\\n")
        ...
        >>> # From another task (e.g., WebSocket message handler)
        >>> await handler.add_message("User's follow-up question")
        >>> await handler.add_message({"type": "text", "text": "More input"})
    """

    def __init__(self, session_id: str):
        """Initialize the streaming input handler.

        Args:
            session_id: The session identifier for the conversation.
        """
        self.session_id = session_id
        self._message_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._is_complete = False

    async def add_message(
        self,
        content: str | list,
        parent_tool_use_id: str | None = None
    ) -> None:
        """Add a message to the streaming queue.

        Messages are processed in FIFO order. Content is normalized
        before being added to the queue.

        Args:
            content: The message content (string or multi-part list).
            parent_tool_use_id: Optional tool use ID for tool responses.

        Raises:
            ValueError: If content normalization fails.
        """
        try:
            # Normalize content to SDK format
            normalized = await asyncio.to_thread(
                normalize_content, content
            )

            # Convert ContentBlock objects to dicts for JSON serialization
            content_dicts = [block.model_dump() for block in normalized]

            # Create message in SDK format
            message = {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": content_dicts
                },
                "parent_tool_use_id": parent_tool_use_id,
                "session_id": self.session_id
            }

            await self._message_queue.put(message)
            logger.debug(f"Added message to queue for session {self.session_id}")

        except Exception as e:
            logger.error(f"Error adding message to queue: {e}", exc_info=True)
            raise ValueError(f"Failed to add message: {e}") from e

    async def add_raw_message(self, message: dict[str, Any]) -> None:
        """Add a pre-formatted message to the queue.

        Use this when you have a message already in SDK format and want
        to bypass content normalization.

        Args:
            message: A message dictionary matching SDK format.
        """
        await self._message_queue.put(message)
        logger.debug(f"Added raw message to queue for session {self.session_id}")

    def complete(self) -> None:
        """Signal that no more messages will be added.

        After calling complete(), the generator will stop yielding messages
        once the queue is exhausted. This allows for clean shutdown of
        the streaming session.
        """
        self._is_complete = True
        logger.debug(f"Marked stream as complete for session {self.session_id}")

    async def generate_messages(
        self
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Generate messages from the queue sequentially.

        This async generator yields messages as they become available in
        the queue. It terminates when complete() is called and the queue
        is empty.

        Yields:
            Message dictionaries in SDK format.

        Examples:
            >>> handler = StreamingInputHandler("session-123")
            >>> # In one task, consume messages
            >>> async for msg in handler.generate_messages():
            ...     await sdk_client.query(msg)
            ...
            >>> # In another task, add messages
            >>> await handler.add_message("First message")
            >>> await handler.add_message("Second message")
            >>> handler.complete()
        """
        try:
            while True:
                # Wait for a message with timeout to check completion status
                try:
                    message = await asyncio.wait_for(
                        self._message_queue.get(),
                        timeout=0.1
                    )
                    yield message
                except asyncio.TimeoutError:
                    # Check if we should stop
                    if self._is_complete and self._message_queue.empty():
                        logger.debug(f"Generator completed for session {self.session_id}")
                        return
                    # Otherwise, continue waiting for messages
                    continue

        except Exception as e:
            logger.error(f"Error in message generator: {e}", exc_info=True)
            raise

    def has_pending_messages(self) -> bool:
        """Check if there are messages waiting in the queue.

        Returns:
            True if the queue has messages, False otherwise.
        """
        return not self._message_queue.empty()

    async def wait_until_empty(self) -> None:
        """Wait until all queued messages have been processed.

        This is useful for synchronization when you need to ensure
        all messages have been yielded before proceeding.
        """
        while not self._message_queue.empty():
            await asyncio.sleep(0.01)
