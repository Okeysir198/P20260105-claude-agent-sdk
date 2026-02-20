"""Direct Python SDK wrapper for Claude Agent SDK.

Provides a client interface that wraps ConversationSession from agent.core
and exposes methods compatible with the API client.
"""
from collections.abc import AsyncIterator

from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk.types import (
    AssistantMessage,
    Message,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from agent.core.agent_options import create_agent_sdk_options
from agent.core.agents import get_agents_info
from agent.core.storage import SessionStorage, get_user_session_storage
from agent.core.subagents import get_subagents_info
from cli.clients.event_normalizer import to_success_event, to_tool_use_event


class DirectClient:
    """Direct Python SDK wrapper that provides API-compatible interface."""

    def __init__(self, username: str | None = None):
        """Initialize the direct client.

        Args:
            username: Username for per-user storage. If None, storage is disabled.
        """
        self._client: ClaudeSDKClient | None = None
        self.session_id: str | None = None
        self._first_message: str | None = None
        self._username = username
        self._storage: SessionStorage | None = get_user_session_storage(username) if username else None

    async def create_session(self, resume_session_id: str | None = None) -> dict:
        """Create or resume a conversation session.

        Args:
            resume_session_id: Optional session ID to resume.

        Returns:
            Dictionary with session information including session_id.
        """
        await self.disconnect()

        options = create_agent_sdk_options(resume_session_id=resume_session_id)
        self._client = ClaudeSDKClient(options)
        await self._client.connect()

        if resume_session_id:
            self.session_id = resume_session_id
        else:
            self.session_id = None

        return {
            "session_id": self.session_id or "pending",
            "status": "connected",
            "resumed": resume_session_id is not None,
        }

    async def send_message(self, content: str, session_id: str | None = None) -> AsyncIterator[dict]:
        """Send a message and stream response events.

        Args:
            content: User message content.
            session_id: Optional session_id (ignored in direct mode).

        Yields:
            Dictionary events representing response stream.
        """
        if not self._client:
            raise RuntimeError("Session not created. Call create_session() first.")

        if self._first_message is None:
            self._first_message = content

        await self._client.query(content)

        async for msg in self._client.receive_response():
            event_dict = self._message_to_event(msg)

            if event_dict.get("type") == "init" and "session_id" in event_dict:
                self.session_id = event_dict["session_id"]
                if self._storage:
                    self._storage.save_session(self.session_id, self._first_message)

            yield event_dict

    async def interrupt(self, session_id: str | None = None) -> bool:
        """Interrupt the current task.

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

    async def disconnect(self) -> None:
        """Disconnect the current session."""
        if self._client:
            await self._client.disconnect()
            self._client = None
            self.session_id = None
            self._first_message = None

    def update_turn_count(self, turn_count: int) -> None:
        """Update turn count in storage."""
        if self.session_id and self._storage:
            self._storage.update_session(self.session_id, turn_count=turn_count)

    async def list_skills(self) -> list[dict]:
        """List available skills."""
        return []

    async def list_agents(self) -> list[dict]:
        """List available top-level agents."""
        return get_agents_info()

    async def list_subagents(self) -> list[dict]:
        """List available subagents."""
        return get_subagents_info()

    async def list_sessions(self) -> list[dict]:
        """List session history."""
        if not self._storage:
            return []
        sessions = self._storage.load_sessions()
        return [
            {
                "session_id": s.session_id,
                "first_message": s.first_message,
                "turn_count": s.turn_count,
                "is_current": s.session_id == self.session_id,
            }
            for s in sessions
        ]

    async def close_session(self, session_id: str) -> None:
        """Close a specific session."""
        if self._storage:
            self._storage.delete_session(session_id)
        if self.session_id == session_id:
            await self.disconnect()

    async def resume_previous_session(self) -> dict | None:
        """Resume the previous session.

        Returns:
            Dictionary with session info or None if no previous session.
        """
        if not self._storage:
            return None
        session_ids = self._storage.get_session_ids()
        valid_sessions = [s for s in session_ids if not s.startswith("pending-")]

        if not valid_sessions:
            return None

        resume_id = self._find_previous_session_id(valid_sessions)
        if resume_id:
            return await self.create_session(resume_session_id=resume_id)
        return None

    def _find_previous_session_id(self, valid_sessions: list[str]) -> str | None:
        """Find the previous session ID from a list of valid session IDs."""
        if self.session_id and self.session_id in valid_sessions:
            idx = valid_sessions.index(self.session_id)
            if idx + 1 < len(valid_sessions):
                return valid_sessions[idx + 1]

        for sid in valid_sessions:
            if sid != self.session_id:
                return sid

        return None

    def _message_to_event(self, msg: Message) -> dict:
        """Convert SDK Message to event dictionary."""
        if isinstance(msg, SystemMessage):
            event = {
                "type": msg.subtype,
                "role": "system",
            }
            if msg.subtype == "init" and hasattr(msg, "data"):
                event["session_id"] = msg.data.get("session_id")
            return event

        if isinstance(msg, StreamEvent):
            return {
                "type": "stream_event",
                "event": msg.event,
            }

        if isinstance(msg, UserMessage):
            event = {
                "type": "user",
                "role": "user",
            }
            if hasattr(msg, "content"):
                event["content"] = [self._block_to_dict(block) for block in msg.content]
            return event

        if isinstance(msg, AssistantMessage):
            event = {
                "type": "assistant",
                "role": "assistant",
            }
            if hasattr(msg, "content"):
                event["content"] = [self._block_to_dict(block) for block in msg.content]
            return event

        if isinstance(msg, ResultMessage):
            return to_success_event(
                num_turns=msg.num_turns,
                total_cost_usd=msg.total_cost_usd,
            )

        return {
            "type": "unknown",
            "role": "unknown",
            "data": str(msg),
        }

    def _block_to_dict(self, block) -> dict:
        """Convert content block to dictionary."""
        if isinstance(block, TextBlock):
            return {"type": "text", "text": block.text}

        if isinstance(block, ToolUseBlock):
            event = to_tool_use_event(
                name=block.name,
                input_data=block.input if block.input else {},
            )
            event["id"] = block.id
            return event

        if isinstance(block, ToolResultBlock):
            content = block.content
            if isinstance(content, list):
                content = "\n".join(str(item) for item in content)
            elif content is not None:
                content = str(content)
            else:
                content = ""

            return {
                "type": "tool_result",
                "tool_use_id": block.tool_use_id,
                "content": content,
                "is_error": getattr(block, "is_error", False),
            }

        return {"type": "unknown", "data": str(block)}
