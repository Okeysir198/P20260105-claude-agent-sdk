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
                # Session already in memory, use stream_message instead
                logger.info(f"[create_and_stream] Session {resume_session_id} already in memory, delegating to stream_message")
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
        logger.info(f"[create_and_stream] Starting with client {id(client)}, resume_session_id={resume_session_id}")

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
                                # For NEW sessions: use pending-xxx as key (frontend will use real SDK ID later)
                                # For RESUMED sessions: use real SDK ID as key
                                if is_resuming:
                                    session_key = sdk_session_id
                                    logger.info(f"[create_and_stream] Registering resumed session: {session_key}")
                                else:
                                    session_key = f"pending-{int(time.time() * 1000)}"
                                    logger.info(f"[create_and_stream] Registering new session: {session_key} -> {sdk_session_id}")

                                session_state = await self.session_manager.register_session(
                                    session_key, client, real_session_id=sdk_session_id, first_message=content, user_id=user_id
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
                    logger.info(f"[create_and_stream] Session {real_session_id} marked as idle")

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
        logger.info(f"[stream_message] session_id={session_id}, content={content[:50]}...")
        print(f"[DEBUG] stream_message called with session_id={session_id}", flush=True)

        # Check if session exists in SessionManager (by either session_id or real_session_id)
        session = await self.session_manager.find_by_session_or_real_id(session_id)
        print(f"[DEBUG] Session found: {session is not None}, if session: {session.real_session_id if session else None}", flush=True)

        history = get_history_storage()
        # Determine the real SDK ID for history files
        # If session found, use its real_session_id; otherwise use the session_id parameter
        sdk_id_for_history = session.real_session_id if session and session.real_session_id else session_id
        ctx = StreamingContext()
        buffered_user_message = content
        is_pending = session_id.startswith("pending-")  # Initialize is_pending upfront
        session_registered = False  # Initialize session_registered upfront

        if session:
            # Use persistent client from SessionManager with locking
            # The session is stored under pending_id key, but found via real_session_id
            print(f"[DEBUG] Found session in SessionManager", flush=True)
            print(f"[DEBUG]   session.session_id (pending key): {session.session_id}", flush=True)
            print(f"[DEBUG]   session.real_session_id (for history): {session.real_session_id}", flush=True)
            print(f"[DEBUG]   session.status: {session.status}", flush=True)

            client = session.client
            logger.info(f"[stream_message] Reusing existing client {id(client)} for session {session_id}, status={session.status}")

            # Acquire session lock to prevent concurrent queries with timeout
            try:
                async with asyncio.timeout(LOCK_TIMEOUT_SECONDS):
                    async with session.lock:
                        print(f"[DEBUG] Acquired lock, status is: {session.status}", flush=True)
                        if session.status != "idle":
                            print(f"[DEBUG] Session is NOT idle! status={session.status}", flush=True)
                            raise ValueError(f"Session {session_id} is already processing a message (status={session.status})")

                        session.status = "active"
                        logger.info(f"[stream_message] Session {session_id} acquired lock, starting query")

                        try:
                            await client.query(content)
                            msg_count = 0

                            async for msg in client.receive_response():
                                msg_count += 1
                                msg_type = type(msg).__name__
                                print(f"[DEBUG] stream_message: Message #{msg_count}: {msg_type}", flush=True)

                                # Handle SystemMessage for pending sessions (first message)
                                # Pending sessions created via POST /api/v1/sessions don't have real_session_id yet
                                if isinstance(msg, SystemMessage):
                                    if msg.subtype == "init" and msg.data and not session.real_session_id:
                                        sdk_session_id = msg.data.get("session_id")
                                        if sdk_session_id:
                                            print(f"[DEBUG] Got real SDK ID for pending session: {sdk_session_id}", flush=True)
                                            # Update the session's real_session_id
                                            session.real_session_id = sdk_session_id
                                            # Update the session's first_message with current content
                                            session.first_message = content
                                            # Update sdk_id_for_history for this request
                                            sdk_id_for_history = sdk_session_id
                                            # Save to storage with real SDK ID and first message
                                            self.session_manager._storage.save_session(
                                                sdk_session_id,
                                                first_message=content,  # Use current content as first message
                                                user_id=session.user_id,
                                            )
                                            logger.info(f"[stream_message] Updated pending session {session.session_id} with real ID: {sdk_session_id}")
                                            # Yield the real session ID to client
                                            yield {"event": "session_id", "data": {"session_id": sdk_session_id}}
                                    continue

                                # Process other message types
                                for event in process_message(msg, ctx):
                                    yield event

                                # Save history when ResultMessage is received (end of turn)
                                if isinstance(msg, ResultMessage):
                                    # Always use sdk_id_for_history (real SDK ID) for history files
                                    # NEVER use the pending ID for history files
                                    print(f"[DEBUG] ResultMessage received", flush=True)
                                    print(f"[DEBUG]   Saving history to: {sdk_id_for_history}", flush=True)
                                    print(f"[DEBUG]   (pending key: {session.session_id})", flush=True)
                                    # Save user message
                                    history.append_message(sdk_id_for_history, "user", content)
                                    # Save assistant message
                                    history.append_message(
                                        sdk_id_for_history,
                                        "assistant",
                                        ctx.accumulated_text,
                                        tool_use=ctx.tool_uses or None,
                                        tool_results=ctx.tool_results or None,
                                    )
                                    print(f"[DEBUG] History saved successfully", flush=True)

                        finally:
                            session.status = "idle"
                            logger.info(f"[stream_message] Session {session_id} released lock, query complete")

            except asyncio.TimeoutError:
                logger.error(f"Lock timeout for session {session_id}")
                yield {"event": "error", "data": {"message": "Session busy, please try again", "session_id": session_id}}
                return

        else:
            # Session not in memory, need to create/reconnect
            print(f"[DEBUG] Session NOT found in SessionManager", flush=True)
            print(f"[DEBUG]   session_id parameter: {session_id}", flush=True)
            print(f"[DEBUG]   is_pending: {is_pending}", flush=True)

            # IMPORTANT: If frontend sends pending-xxx but session not in memory,
            # we cannot resume the original conversation. Reject with error.
            if is_pending:
                logger.error(f"[stream_message] Pending session {session_id} not found - cannot resume")
                yield {
                    "event": "error",
                    "data": {
                        "message": "Session expired or not found. Please start a new conversation.",
                        "session_id": session_id,
                        "error_code": "SESSION_NOT_FOUND",
                    },
                }
                return

            resume_id = session_id  # Use real SDK ID for resuming

            logger.info(f"[stream_message] Creating new client for session {session_id}")
            client = ClaudeSDKClient(create_enhanced_options(resume_session_id=resume_id))
            await client.connect()

            # Double-checked locking: verify session still doesn't exist after client creation
            # Another request might have created it while we were connecting
            existing_session = await self.session_manager.find_by_session_or_real_id(session_id)
            if existing_session:
                # Session was created by another request, disconnect our new client and use existing
                logger.info(f"[stream_message] Session {session_id} was created by another request, reusing")
                try:
                    await client.disconnect()
                except Exception as e:
                    logger.warning(f"Failed to disconnect redundant client: {e}")
                # Recursively call stream_message to use the existing session
                async for event in self.stream_message(session_id, content):
                    yield event
                return

            try:
                await client.query(content)
                msg_count = 0

                async for msg in client.receive_response():
                    msg_count += 1
                    logger.info(f"[stream_message] Message #{msg_count}: {type(msg).__name__}")

                    # Handle SystemMessage to capture real session ID for resumed sessions
                    if isinstance(msg, SystemMessage):
                        if msg.subtype == "init" and msg.data:
                            sdk_session_id = msg.data.get("session_id")
                            if sdk_session_id:
                                print(f"[DEBUG] Resumed session got SDK ID: {sdk_session_id}", flush=True)
                                sdk_id_for_history = sdk_session_id
                        continue

                    for event in process_message(msg, ctx):
                        yield event

                    # Save history when ResultMessage is received (end of turn)
                    if isinstance(msg, ResultMessage):
                        # Always use sdk_id_for_history (real SDK ID) for history files
                        print(f"[DEBUG] ResultMessage (resumed session)", flush=True)
                        print(f"[DEBUG]   Saving history to: {sdk_id_for_history}", flush=True)
                        # Save user message
                        history.append_message(sdk_id_for_history, "user", content)
                        # Save assistant message
                        history.append_message(
                            sdk_id_for_history,
                            "assistant",
                            ctx.accumulated_text,
                            tool_use=ctx.tool_uses or None,
                            tool_results=ctx.tool_results or None,
                        )
                        print(f"[DEBUG] History saved successfully (resumed session)", flush=True)

                # Register the resumed session with SessionManager
                if not session_registered:
                    # Use sdk_id_for_history as both key and real_session_id
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
                # Yield error event to client
                yield {"event": "error", "data": {"message": str(e), "session_id": session_id}}
                raise
            finally:
                # If session was registered, mark it as idle
                if session_registered:
                    # Find the session and set status to idle
                    new_session_state = await self.session_manager.find_by_session_or_real_id(sdk_id_for_history)
                    if new_session_state:
                        new_session_state.status = "idle"

        yield {
            "event": "done",
            "data": {
                "session_id": sdk_id_for_history,  # Always use the real SDK ID
                "turn_count": ctx.turn_count,
                "total_cost_usd": ctx.total_cost,
            },
        }

        # Note: Client stays connected in SessionManager for next message
        # Only disconnect on: close_session, delete_session, resume_session, server shutdown

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
