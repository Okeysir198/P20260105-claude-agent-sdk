"""Conversation session management with Skills and Subagents support."""
import asyncio
from collections.abc import AsyncIterator

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from claude_agent_sdk.types import Message, ResultMessage

from agent.core.agent_options import create_agent_sdk_options
from agent.core.storage import SessionStorage
from agent.display import print_info, print_message, print_success, process_messages


class ConversationSession:
    """Maintains a single conversation session with Claude.

    Use connect()/send_message()/disconnect() for automated conversations.
    """

    def __init__(
        self,
        options: ClaudeAgentOptions | None = None,
        include_partial_messages: bool = True,
        agent_id: str | None = None,
        storage: SessionStorage | None = None
    ):
        self.client = ClaudeSDKClient(options)
        self.turn_count: int = 0
        self.session_id: str | None = None  # API-level session ID (pending-xxx)
        self.sdk_session_id: str | None = None  # SDK-level session ID for multi-turn context
        self._session_shown: bool = False
        self._first_message: str | None = None
        self._storage: SessionStorage | None = storage
        self._include_partial_messages: bool = include_partial_messages
        self._connected: bool = False
        self._agent_id: str | None = agent_id

    @property
    def is_connected(self) -> bool:
        """Whether the session is currently connected."""
        return self._connected

    async def send_query(self, content: str | AsyncIterator[str]) -> AsyncIterator[Message]:
        """Send query and yield response messages. Accepts string or async iterator."""
        if not self._connected:
            await self.connect()

        # Send query (SDK handles both string and AsyncIterator)
        await self.client.query(content)

        # Stream responses, break on ResultMessage
        async for msg in self.client.receive_response():
            yield msg
            if isinstance(msg, ResultMessage):
                break

        self.turn_count += 1

    async def shutdown(self) -> None:
        """Gracefully shutdown the session. Alias for disconnect()."""
        await self.disconnect()

    async def connect(self) -> None:
        """Connect the session to Claude SDK. Must be called before sending messages."""
        if self._connected:
            raise RuntimeError("Session is already connected")

        await self.client.connect()
        self._connected = True

    def _on_session_id(self, session_id: str) -> None:
        """Handle session ID from init message."""
        self.session_id = session_id
        print_info(f"Session ID: {session_id}")
        if self._storage:
            self._storage.save_session(session_id)
        self._session_shown = True

    async def send_message(self, prompt: str) -> None:
        """Send a message programmatically and display the response."""
        if not self._connected:
            raise RuntimeError("Session not connected. Call connect() first.")

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
        """Disconnect the session and cleanup."""
        if self._connected:
            await self.client.disconnect()
            self._connected = False

    def get_session_info(self) -> dict:
        """Get current session_id, turn_count, and connected status."""
        return {
            "session_id": self.session_id,
            "turn_count": self.turn_count,
            "connected": self._connected
        }

    async def start(self) -> None:
        """Connect the session and print a startup message."""
        await self.connect()
        print_success("Conversation session started with Skills and Subagents enabled.")
        print_info("Use send_message() to send messages programmatically.")


async def main() -> None:
    """Demo: Programmatic conversation with Skills and Subagents enabled."""
    options = create_agent_sdk_options()
    session = ConversationSession(options)

    await session.start()
    await session.send_message("What is 2 + 2?")
    await session.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
