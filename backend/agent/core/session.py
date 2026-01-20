"""Conversation session management for Claude Agent SDK.

Contains the ConversationSession class for managing programmatic conversations
with Skills and Subagents support.
"""
import asyncio
from typing import AsyncIterator

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk.types import Message

from agent.core.agent_options import create_enhanced_options
from agent.core.storage import get_storage
from agent.display import print_success, print_info, print_message, process_messages


class ConversationSession:
    """Maintains a single conversation session with Claude.

    Provides programmatic conversation management with Skills and Subagents.
    Use connect()/send_message()/disconnect() for automated conversations.

    Attributes:
        client: ClaudeSDKClient instance for SDK communication.
        turn_count: Number of completed conversation turns.
        session_id: Current session identifier (assigned on first message).
    """

    def __init__(
        self,
        options: ClaudeAgentOptions | None = None,
        include_partial_messages: bool = True
    ):
        """Initialize conversation session.

        Args:
            options: Optional ClaudeAgentOptions. If None, uses default options.
            include_partial_messages: Whether to include partial messages in responses.
                                      Default: True for streaming responses.
        """
        self.client = ClaudeSDKClient(options)
        self.turn_count = 0
        self.session_id = None
        self._session_shown = False
        self._first_message = None
        self._storage = get_storage()
        self._include_partial_messages = include_partial_messages
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if the session is connected.

        Returns:
            bool: True if connected, False otherwise.
        """
        return self._connected

    async def connect(self) -> None:
        """Connect the session to Claude SDK.

        Must be called before sending messages.

        Raises:
            RuntimeError: If already connected.
        """
        if self._connected:
            raise RuntimeError("Session is already connected")

        await self.client.connect()
        self._connected = True

    def _on_session_id(self, session_id: str) -> None:
        """Handle session ID from init message.

        Args:
            session_id: Session ID received from SDK.
        """
        self.session_id = session_id
        print_info(f"Session ID: {session_id}")
        self._storage.save_session(session_id)
        self._session_shown = True

    async def send_message(self, prompt: str) -> None:
        """Send a message programmatically (non-interactive mode).

        This method allows programmatic sending of messages without the REPL loop.
        Useful for testing and automated conversations.

        Args:
            prompt: The user's message prompt.

        Raises:
            RuntimeError: If session is not connected. Call connect() first.

        Example:
            session = ConversationSession(options)
            await session.connect()
            await session.send_message("What is 2 + 2?")
            await session.send_message("What about 5 + 3?")
            await session.disconnect()
        """
        if not self._connected:
            raise RuntimeError("Session not connected. Call connect() first.")

        # Send and process message
        await print_message("user", prompt)

        async def get_response() -> AsyncIterator[Message]:
            await self.client.query(prompt)
            async for msg in self.client.receive_response():
                yield msg

        await process_messages(
            get_response(),
            stream=self._include_partial_messages,
            on_session_id=None if self._session_shown else self._on_session_id
        )

        self.turn_count += 1

    async def disconnect(self) -> None:
        """Disconnect the session and cleanup.

        Saves session metadata to storage before disconnecting.
        """
        if self._connected:
            await self.client.disconnect()
            self._connected = False

    def get_session_info(self) -> dict:
        """Get current session information.

        Returns:
            Dictionary with session_id, turn_count, and connected status.
        """
        return {
            "session_id": self.session_id,
            "turn_count": self.turn_count,
            "connected": self._connected
        }

    async def start(self) -> None:
        """Start the conversation session.

        Convenience method that connects the session. Use send_message()
        for programmatic message sending.

        Example:
            session = ConversationSession(options)
            await session.start()
            await session.send_message("Hello!")
            await session.disconnect()
        """
        await self.connect()
        print_success("Conversation session started with Skills and Subagents enabled.")
        print_info("Use send_message() to send messages programmatically.")


async def main() -> None:
    """Demo: Programmatic conversation with Skills and Subagents enabled."""
    options = create_enhanced_options()
    session = ConversationSession(options)

    await session.start()
    await session.send_message("What is 2 + 2?")
    await session.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
