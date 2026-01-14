"""Conversation service for handling Claude SDK interactions."""

import logging
from typing import AsyncIterator, Any, Optional

from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk.types import (
    SystemMessage,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

from agent.core.agent_options import create_enhanced_options
from api.services.session_manager import SessionManager
from api.services.history_storage import get_history_storage
from api.services.message_utils import (
    StreamingContext,
    process_message,
    convert_message_to_dict,
)

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for handling conversation logic with Claude SDK."""

    def __init__(self, session_manager: SessionManager) -> None:
        """Initialize conversation service."""
        self.session_manager = session_manager

    async def create_and_stream(
        self,
        content: str,
        resume_session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Create a new session and stream the first message response.

        Uses connect() for proper client initialization.
        Client is kept alive for subsequent messages.

        Args:
            content: First message content
            resume_session_id: Optional session ID to resume
            agent_id: Optional agent ID to use specific agent configuration

        Yields:
            SSE-formatted event dictionaries including session_id event
        """
        client = ClaudeSDKClient(
            create_enhanced_options(resume_session_id=resume_session_id, agent_id=agent_id)
        )
        await client.connect()

        real_session_id = resume_session_id
        history = get_history_storage()
        session_registered = False
        ctx = StreamingContext()

        await client.query(content)

        async for msg in client.receive_response():
            # Handle SystemMessage to capture real session ID
            if isinstance(msg, SystemMessage):
                if msg.subtype == "init" and msg.data:
                    sdk_session_id = msg.data.get("session_id")
                    if sdk_session_id:
                        real_session_id = sdk_session_id
                        if not session_registered:
                            await self.session_manager.register_session(
                                real_session_id, client, content
                            )
                            session_registered = True
                            history.append_message(real_session_id, "user", content)
                        yield {"event": "session_id", "data": {"session_id": sdk_session_id}}
                continue

            # Process message and yield SSE events
            for event in process_message(msg, ctx):
                yield event

        # Save assistant response to history
        if real_session_id:
            history.append_message(
                real_session_id,
                "assistant",
                ctx.accumulated_text,
                tool_use=ctx.tool_uses or None,
                tool_results=ctx.tool_results or None,
            )

        yield {
            "event": "done",
            "data": {"session_id": real_session_id, "turn_count": ctx.turn_count},
        }

    async def send_message(
        self,
        session_id: str,
        content: str,
    ) -> dict[str, Any]:
        """Send a message and get the complete response (non-streaming).

        Uses the persistent client stored in SessionManager.

        Args:
            session_id: Session ID
            content: User message content

        Returns:
            Dictionary with response data

        Raises:
            ValueError: If session not found
        """
        session = await self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        client = session.client
        await client.query(content)

        messages = []
        response_text = ""
        tool_uses = []
        turn_count = 0

        async for msg in client.receive_response():
            if isinstance(msg, SystemMessage):
                continue

            messages.append(convert_message_to_dict(msg))

            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        response_text += block.text
                    elif isinstance(block, ToolUseBlock):
                        tool_uses.append({"name": block.name, "input": block.input})

            if isinstance(msg, ResultMessage):
                turn_count = msg.num_turns

        return {
            "session_id": session_id,
            "response": response_text,
            "tool_uses": tool_uses,
            "turn_count": turn_count,
            "messages": messages,
        }

    async def stream_message(
        self,
        session_id: str,
        content: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """Send a message to an existing session and stream the response.

        Creates a fresh client with resume_session_id to continue the conversation.
        The Claude SDK requires a new client connection for each query.

        For pending sessions (not yet assigned a real session ID), creates a new
        conversation and yields the real session_id.

        Args:
            session_id: Session ID to continue
            content: User message content

        Yields:
            SSE-formatted event dictionaries

        Raises:
            ValueError: If session not found in history
        """
        logger.info(f"[stream_message] session_id={session_id}, content={content[:50]}...")

        # Check if this is a pending session (no real Claude session yet)
        is_pending = session_id.startswith("pending-")

        # For pending sessions, don't pass resume_session_id (new conversation)
        # For established sessions (UUID format), resume with the session ID
        # Note: We don't strictly validate session existence here - Claude SDK will
        # handle invalid session IDs naturally, and strict validation can fail
        # due to timing between session creation and subsequent messages
        resume_id = None if is_pending else session_id
        logger.info(f"[stream_message] Creating client with resume_session_id={resume_id}...")

        client = ClaudeSDKClient(create_enhanced_options(resume_session_id=resume_id))
        await client.connect()

        history = get_history_storage()
        real_session_id = session_id  # Will be updated for pending sessions
        session_registered = False

        logger.info("[stream_message] Sending query...")
        await client.query(content)
        logger.info("[stream_message] Starting response iteration...")

        ctx = StreamingContext()
        msg_count = 0

        async for msg in client.receive_response():
            msg_count += 1
            logger.info(f"[stream_message] Message #{msg_count}: {type(msg).__name__}")

            # Handle SystemMessage to capture real session ID for pending sessions
            if isinstance(msg, SystemMessage):
                if is_pending and msg.subtype == "init" and msg.data:
                    sdk_session_id = msg.data.get("session_id")
                    if sdk_session_id:
                        real_session_id = sdk_session_id
                        logger.info(f"[stream_message] Got real session_id: {real_session_id}")
                        # Update pending session to use real ID (moves entry, no disconnect)
                        if not session_registered:
                            await self.session_manager.update_session_id(
                                session_id, real_session_id, content
                            )
                            session_registered = True
                        # Yield the real session ID to client
                        yield {"event": "session_id", "data": {"session_id": sdk_session_id}}
                continue

            for event in process_message(msg, ctx):
                yield event

        # Save messages to history with real session ID
        history.append_message(real_session_id, "user", content)
        history.append_message(
            real_session_id,
            "assistant",
            ctx.accumulated_text,
            tool_use=ctx.tool_uses or None,
            tool_results=ctx.tool_results or None,
        )

        yield {
            "event": "done",
            "data": {
                "session_id": real_session_id,
                "turn_count": ctx.turn_count,
                "total_cost_usd": ctx.total_cost,
            },
        }

        # Cleanup - disconnect since we create fresh clients for each query
        try:
            await client.disconnect()
        except Exception:
            pass

    async def interrupt(self, session_id: str) -> bool:
        """Interrupt the current task for a session.

        Args:
            session_id: Session ID

        Returns:
            True if interrupted successfully

        Raises:
            ValueError: If session not found
        """
        session_state = await self.session_manager.get_session(session_id)
        if not session_state:
            raise ValueError(f"Session {session_id} not found")

        await session_state.client.interrupt()
        return True
