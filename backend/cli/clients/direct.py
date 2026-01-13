"""Direct Python SDK wrapper for Claude Agent SDK.

Provides a client interface that wraps ConversationSession from agent.core
and exposes methods compatible with the API client.
"""
from typing import AsyncIterator, Optional

from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk.types import (
    Message,
    AssistantMessage,
    UserMessage,
    SystemMessage,
    ResultMessage,
    StreamEvent,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
)

from agent.core.agent_options import create_enhanced_options
from agent.core.storage import get_storage
from agent.core.subagents import get_agents_info as get_subagents_info
from agent.core.agents import get_agents_info
from agent.discovery.skills import discover_skills


class DirectClient:
    """Direct Python SDK wrapper that provides API-compatible interface."""

    def __init__(self):
        """Initialize the direct client."""
        self._client: Optional[ClaudeSDKClient] = None
        self.session_id: Optional[str] = None
        self._first_message: Optional[str] = None
        self._storage = get_storage()

    async def create_session(self, resume_session_id: Optional[str] = None) -> dict:
        """Create or resume a conversation session.

        Args:
            resume_session_id: Optional session ID to resume.

        Returns:
            Dictionary with session information including session_id.
        """
        # Disconnect any existing client first to ensure clean state
        await self.disconnect()

        # Create and connect new client
        options = create_enhanced_options(resume_session_id=resume_session_id)
        self._client = ClaudeSDKClient(options)
        await self._client.connect()

        # Set session ID
        if resume_session_id:
            self.session_id = resume_session_id
        else:
            # Will be set on first message when we get init message
            self.session_id = None

        return {
            "session_id": self.session_id or "pending",
            "status": "connected",
            "resumed": resume_session_id is not None
        }

    async def send_message(self, content: str, session_id: Optional[str] = None) -> AsyncIterator[dict]:
        """Send a message and stream response events.

        Args:
            content: User message content.
            session_id: Optional session_id (ignored in direct mode, for API compatibility).

        Yields:
            Dictionary events representing response stream.
        """
        if not self._client:
            raise RuntimeError("Session not created. Call create_session() first.")

        # Track first message for session metadata
        if self._first_message is None:
            self._first_message = content

        # Send query (no reconnection needed - client persists)
        await self._client.query(content)

        # Stream response messages
        async for msg in self._client.receive_response():
            event_dict = self._message_to_event(msg)

            # Capture session ID from init message and save with first message
            if event_dict.get("type") == "init" and "session_id" in event_dict:
                self.session_id = event_dict["session_id"]
                # Save session with first message to unified storage
                self._storage.save_session(self.session_id, self._first_message)

            yield event_dict

    async def interrupt(self, session_id: Optional[str] = None) -> bool:
        """Interrupt the current task.

        Args:
            session_id: Optional session_id (ignored in direct mode, for API compatibility).

        Returns:
            True if interrupt was successful.
        """
        if not self._client:
            return False

        try:
            await self._client.interrupt()
            return True
        except Exception:
            return False

    async def disconnect(self):
        """Disconnect the current session."""
        if self._client:
            await self._client.disconnect()
            self._client = None
            self.session_id = None
            self._first_message = None

    def update_turn_count(self, turn_count: int) -> None:
        """Update turn count in storage.

        Args:
            turn_count: Current turn count to save.
        """
        if self.session_id:
            self._storage.update_session(self.session_id, turn_count=turn_count)

    async def list_skills(self) -> list[dict]:
        """List available skills.

        Returns:
            List of skill dictionaries with name and description.
        """
        return discover_skills()

    async def list_agents(self) -> list[dict]:
        """List available top-level agents (for agent_id selection).

        Returns:
            List of agent dictionaries with agent_id, name, type, etc.
        """
        return get_agents_info()

    async def list_subagents(self) -> list[dict]:
        """List available subagents (for delegation within conversations).

        Returns:
            List of subagent dictionaries with name and focus.
        """
        return get_subagents_info()

    async def list_sessions(self) -> list[dict]:
        """List session history.

        Returns:
            List of session dictionaries with session_id and metadata.
        """
        sessions = self._storage.load_sessions()
        return [
            {
                "session_id": s.session_id,
                "first_message": s.first_message,
                "turn_count": s.turn_count,
                "is_current": s.session_id == self.session_id
            }
            for s in sessions
        ]

    async def close_session(self, session_id: str) -> None:
        """Close a specific session.

        In direct mode, this removes the session from storage.

        Args:
            session_id: Session ID to close.
        """
        self._storage.delete_session(session_id)
        if self.session_id == session_id:
            await self.disconnect()

    def _message_to_event(self, msg: Message) -> dict:
        """Convert SDK Message to event dictionary.

        Args:
            msg: SDK Message object.

        Returns:
            Dictionary representation of the message event.
        """
        # Use isinstance checks to handle different message types correctly
        if isinstance(msg, SystemMessage):
            event = {
                "type": msg.subtype,  # SystemMessage uses 'subtype' not 'type'
                "role": "system",
            }
            # Add session_id for init messages
            if msg.subtype == "init" and hasattr(msg, 'data'):
                event["session_id"] = msg.data.get('session_id')

        elif isinstance(msg, StreamEvent):
            event = {
                "type": "stream_event",
                "event": msg.event,
            }

        elif isinstance(msg, UserMessage):
            event = {
                "type": "user",  # Use hardcoded string instead of msg.type
                "role": "user",
            }
            # Handle content blocks
            if hasattr(msg, 'content'):
                event["content"] = [self._block_to_dict(block) for block in msg.content]

        elif isinstance(msg, AssistantMessage):
            event = {
                "type": "assistant",  # Use hardcoded string instead of msg.type
                "role": "assistant",
            }
            # Handle content blocks
            if hasattr(msg, 'content'):
                event["content"] = [self._block_to_dict(block) for block in msg.content]

        elif isinstance(msg, ResultMessage):
            event = {
                "type": msg.subtype,  # ResultMessage uses 'subtype'
                "role": "system",
                "num_turns": msg.num_turns,
                "total_cost_usd": msg.total_cost_usd,
            }

        else:
            # Fallback for unknown message types
            event = {
                "type": "unknown",
                "role": "unknown",
                "data": str(msg),
            }

        return event

    def _block_to_dict(self, block) -> dict:
        """Convert content block to dictionary.

        Args:
            block: Content block (TextBlock, ToolUseBlock, etc.)

        Returns:
            Dictionary representation of the block.
        """
        if isinstance(block, TextBlock):
            return {
                "type": "text",
                "text": block.text
            }
        elif isinstance(block, ToolUseBlock):
            return {
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input if block.input else {}
            }
        elif isinstance(block, ToolResultBlock):
            # Convert content to string for proper display
            content = block.content
            if content is None:
                content = ""
            elif not isinstance(content, str):
                # Handle different content types
                if isinstance(content, list):
                    # Join list items
                    content = "\n".join(str(item) for item in content)
                else:
                    content = str(content)

            return {
                "type": "tool_result",
                "tool_use_id": block.tool_use_id,
                "content": content,
                "is_error": block.is_error if hasattr(block, 'is_error') else False
            }
        else:
            # Fallback for unknown block types
            return {"type": "unknown", "data": str(block)}
