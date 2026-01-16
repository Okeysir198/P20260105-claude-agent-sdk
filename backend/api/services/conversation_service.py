"""Conversation service for handling Claude SDK interactions."""

import asyncio
import logging
import time
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

# Lock acquisition timeout in seconds
LOCK_TIMEOUT_SECONDS = 30


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
        user_id: Optional[str] = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Create a new session and stream the first message response.

        Uses connect() for proper client initialization.
        Client is kept alive for subsequent messages.

        Args:
            content: First message content
            resume_session_id: Optional real SDK session ID to resume (NOT pending-xxx)
            agent_id: Optional agent ID to use specific agent configuration
            user_id: Optional user ID for multi-user tracking

        Yields:
            SSE-formatted event dictionaries including session_id event
        """
        # Check if session already exists in memory
        if resume_session_id:
            existing_session = await self.session_manager.find_by_session_or_real_id(resume_session_id)
            if existing_session:
                logger.info(f"Session {resume_session_id} already in memory, reusing")
                async for event in self.stream_message(resume_session_id, content, user_id):
                    yield event
                return

        client = ClaudeSDKClient(
            create_enhanced_options(resume_session_id=resume_session_id, agent_id=agent_id)
        )
        await client.connect()

        real_session_id = resume_session_id
        is_resuming = resume_session_id is not None
        history = get_history_storage()
        session_registered = False
        ctx = StreamingContext()
        logger.info(f"Creating session (resume={resume_session_id}, user={user_id})")

        try:
            await client.query(content)

            async for msg in client.receive_response():
                # Handle SystemMessage to capture real session ID
                if isinstance(msg, SystemMessage):
                    if msg.subtype == "init" and msg.data:
                        sdk_session_id = msg.data.get("session_id")
                        if sdk_session_id:
                            real_session_id = sdk_session_id
                            if not session_registered:
                                # For NEW sessions: use pending-xxx as key
                                # For RESUMED sessions: use real SDK ID as key
                                session_key = sdk_session_id if is_resuming else f"pending-{int(time.time() * 1000)}"

                                session_state = await self.session_manager.register_session(
                                    session_key, client, real_session_id=sdk_session_id,
                                    first_message=content, user_id=user_id
                                )
                                session_state.status = "active"
                                session_registered = True
                                # Save user message with REAL session ID
                                history.append_message(sdk_session_id, "user", content)
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

        except Exception as e:
            logger.error(f"Error during create_and_stream: {e}")
            yield {"event": "error", "data": {"message": str(e), "session_id": real_session_id}}
            raise
        finally:
            # Mark session as idle when done
            if session_registered:
                session = await self.session_manager.find_by_session_or_real_id(real_session_id)
                if session:
                    session.status = "idle"

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
        user_id: Optional[str] = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Send a message to an existing session and stream the response.

        Uses the persistent client stored in SessionManager for efficient
        session reuse. Only creates a new client if the session is not in memory.

        IMPORTANT: Frontend must send the real SDK session ID (not pending-xxx).
        Pending session IDs are only valid while the session is in memory.
        If session expired or server restarted, pending IDs cannot be resumed.

        Args:
            session_id: Real SDK session ID to continue (NOT pending-xxx)
            content: User message content
            user_id: Optional user ID for multi-user tracking

        Yields:
            SSE-formatted event dictionaries

        Raises:
            ValueError: If session not found and cannot be created
        """
        logger.debug(f"stream_message: session={session_id}")

        # Check if session exists in SessionManager
        session = await self.session_manager.find_by_session_or_real_id(session_id)

        history = get_history_storage()
        sdk_id_for_history = session.real_session_id if session and session.real_session_id else session_id
        ctx = StreamingContext()
        is_pending = session_id.startswith("pending-")
        session_registered = False

        if session:
            # Reuse existing client from SessionManager
            client = session.client
            logger.info(f"Reusing client for session {session_id}")

            # Acquire session lock with timeout
            try:
                async with asyncio.timeout(LOCK_TIMEOUT_SECONDS):
                    async with session.lock:
                        if session.status != "idle":
                            raise ValueError(f"Session {session_id} is busy (status={session.status})")

                        session.status = "active"

                        try:
                            await client.query(content)

                            async for msg in client.receive_response():
                                # Handle SystemMessage for pending sessions (first message)
                                if isinstance(msg, SystemMessage):
                                    if msg.subtype == "init" and msg.data and not session.real_session_id:
                                        sdk_session_id = msg.data.get("session_id")
                                        if sdk_session_id:
                                            # Update session with real SDK ID
                                            session.real_session_id = sdk_session_id
                                            session.first_message = content
                                            sdk_id_for_history = sdk_session_id
                                            # Save to storage
                                            self.session_manager._storage.save_session(
                                                sdk_session_id,
                                                first_message=content,
                                                user_id=session.user_id,
                                            )
                                            logger.info(f"Updated pending session with real ID: {sdk_session_id}")
                                            yield {"event": "session_id", "data": {"session_id": sdk_session_id}}
                                    continue

                                # Process message
                                for event in process_message(msg, ctx):
                                    yield event

                                # Save history on ResultMessage
                                if isinstance(msg, ResultMessage):
                                    history.append_message(sdk_id_for_history, "user", content)
                                    history.append_message(
                                        sdk_id_for_history,
                                        "assistant",
                                        ctx.accumulated_text,
                                        tool_use=ctx.tool_uses or None,
                                        tool_results=ctx.tool_results or None,
                                    )

                        finally:
                            session.status = "idle"

            except asyncio.TimeoutError:
                logger.error(f"Lock timeout for session {session_id}")
                yield {"event": "error", "data": {"message": "Session busy, please try again", "session_id": session_id}}
                return

        else:
            # Session not in memory, need to create/reconnect
            # IMPORTANT: Pending sessions not in memory cannot be resumed
            if is_pending:
                logger.error(f"Pending session {session_id} not found - cannot resume")
                yield {
                    "event": "error",
                    "data": {
                        "message": "Session expired or not found. Please start a new conversation.",
                        "session_id": session_id,
                        "error_code": "SESSION_NOT_FOUND",
                    },
                }
                return

            # Resume with real SDK ID
            logger.info(f"Creating new client for session {session_id}")
            client = ClaudeSDKClient(create_enhanced_options(resume_session_id=session_id))
            await client.connect()

            # Double-checked locking: verify session still doesn't exist
            existing_session = await self.session_manager.find_by_session_or_real_id(session_id)
            if existing_session:
                logger.info(f"Session {session_id} created by another request, reusing")
                try:
                    await client.disconnect()
                except Exception as e:
                    logger.warning(f"Failed to disconnect redundant client: {e}")
                async for event in self.stream_message(session_id, content, user_id):
                    yield event
                return

            try:
                await client.query(content)

                async for msg in client.receive_response():
                    # Handle SystemMessage for resumed sessions
                    if isinstance(msg, SystemMessage):
                        if msg.subtype == "init" and msg.data:
                            sdk_session_id = msg.data.get("session_id")
                            if sdk_session_id:
                                sdk_id_for_history = sdk_session_id
                        continue

                    for event in process_message(msg, ctx):
                        yield event

                    # Save history on ResultMessage
                    if isinstance(msg, ResultMessage):
                        history.append_message(sdk_id_for_history, "user", content)
                        history.append_message(
                            sdk_id_for_history,
                            "assistant",
                            ctx.accumulated_text,
                            tool_use=ctx.tool_uses or None,
                            tool_results=ctx.tool_results or None,
                        )

                # Register the resumed session
                if not session_registered:
                    await self.session_manager.register_session(
                        sdk_id_for_history,
                        client,
                        real_session_id=sdk_id_for_history,
                        first_message=content,
                        user_id=user_id,
                    )
                    session_registered = True

            except Exception as e:
                logger.error(f"Error during query for session {session_id}: {e}")
                yield {"event": "error", "data": {"message": str(e), "session_id": session_id}}
                raise
            finally:
                if session_registered:
                    new_session_state = await self.session_manager.find_by_session_or_real_id(sdk_id_for_history)
                    if new_session_state:
                        new_session_state.status = "idle"

        yield {
            "event": "done",
            "data": {
                "session_id": sdk_id_for_history,
                "turn_count": ctx.turn_count,
                "total_cost_usd": ctx.total_cost,
            },
        }

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
