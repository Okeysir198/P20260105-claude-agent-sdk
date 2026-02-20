"""Async generator wrapper for streaming input mode.

Converts user content into the async generator format expected by the
Claude Agent SDK's streaming input mode, supporting both simple strings
and multi-part content (text, images).
"""
import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

from api.services.content_normalizer import normalize_content

logger = logging.getLogger(__name__)


async def _normalize_to_sdk_message(
    content: str | list,
    session_id: str,
    parent_tool_use_id: str | None = None,
) -> dict[str, Any]:
    """Normalize content and wrap it in an SDK-format user message dict."""
    normalized = await asyncio.to_thread(normalize_content, content)
    content_dicts = [block.model_dump() for block in normalized]
    return {
        "type": "user",
        "message": {"role": "user", "content": content_dicts},
        "parent_tool_use_id": parent_tool_use_id,
        "session_id": session_id,
    }


async def create_message_generator(
    content: str | list,
    session_id: str,
    parent_tool_use_id: str | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Create an async generator that yields a single normalized SDK message."""
    try:
        yield await _normalize_to_sdk_message(content, session_id, parent_tool_use_id)
    except Exception as e:
        logger.error(f"Error creating message generator: {e}", exc_info=True)
        raise ValueError(f"Invalid content format: {e}") from e


class StreamingInputHandler:
    """Queue-based streaming input for dynamically adding messages to a conversation.

    Messages added via add_message() are normalized and queued, then yielded
    sequentially by generate_messages(). Call complete() to signal the end
    of the stream.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._message_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._is_complete = False

    async def add_message(
        self,
        content: str | list,
        parent_tool_use_id: str | None = None,
    ) -> None:
        """Normalize content and add it to the streaming queue."""
        try:
            message = await _normalize_to_sdk_message(
                content, self.session_id, parent_tool_use_id
            )
            await self._message_queue.put(message)
            logger.debug(f"Added message to queue for session {self.session_id}")
        except Exception as e:
            logger.error(f"Error adding message to queue: {e}", exc_info=True)
            raise ValueError(f"Failed to add message: {e}") from e

    async def add_raw_message(self, message: dict[str, Any]) -> None:
        """Add a pre-formatted SDK message to the queue, bypassing normalization."""
        await self._message_queue.put(message)
        logger.debug(f"Added raw message to queue for session {self.session_id}")

    def complete(self) -> None:
        """Signal that no more messages will be added."""
        self._is_complete = True
        logger.debug(f"Marked stream as complete for session {self.session_id}")

    async def generate_messages(self) -> AsyncGenerator[dict[str, Any], None]:
        """Yield messages from the queue until complete() is called and queue is empty."""
        try:
            while True:
                try:
                    message = await asyncio.wait_for(
                        self._message_queue.get(), timeout=0.1
                    )
                    yield message
                except asyncio.TimeoutError:
                    if self._is_complete and self._message_queue.empty():
                        logger.debug(f"Generator completed for session {self.session_id}")
                        return
                    continue
        except Exception as e:
            logger.error(f"Error in message generator: {e}", exc_info=True)
            raise

    def has_pending_messages(self) -> bool:
        """Check if there are messages waiting in the queue."""
        return not self._message_queue.empty()

    async def wait_until_empty(self) -> None:
        """Wait until all queued messages have been processed."""
        while not self._message_queue.empty():
            await asyncio.sleep(0.01)
