"""Conversation service for handling Claude SDK interactions."""

import asyncio
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

from api.services.session_manager import SessionManager
from api.services.history_storage import get_history_storage
from api.services.client_pool import ClientPool
from api.services.message_utils import (
    StreamingContext,
    process_message,
    convert_message_to_dict,
)

from api.utils import generate_pending_session_id
logger = logging.getLogger(__name__)

# Constants for session management
PENDING_SESSION_PREFIX = "pending-"
LOCK_TIMEOUT_SECONDS = 30  # Maximum time to wait for session lock acquisition


class ConversationService:
    """Service for handling conversation logic with Claude SDK."""

    def __init__(self, session_manager: SessionManager, client_pool: ClientPool) -> None:
        """Initialize conversation service.

        Args:
            session_manager: Session manager for tracking sessions
            client_pool: Client pool for managing SDK clients
        """
        self.session_manager = session_manager
        self.client_pool = client_pool

    async def create_and_stream(
        self,
        content: str,
        resume_session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Create a new session and stream the first message response.

        Uses client pool for efficient client management.
        Client is acquired from pool and released back after completion.

        Args:
            content: First message content
            resume_session_id: Optional real SDK session ID to resume (NOT pending-xxx)
            agent_id: Optional agent ID to use specific agent configuration
            user_id: Optional user ID for multi-user tracking

        Yields:
            SSE-formatted event dictionaries including session_id event
        """
        # Check if session already exists in memory
        # If so, reuse it instead of creating a new one
        if resume_session_id:
            existing_session = await self.session_manager.find_by_session_or_real_id(resume_session_id)
            if existing_session:
                logger.info(f"Session {resume_session_id} already in memory, reusing for create_and_stream")
                async for event in self.stream_message(resume_session_id, content, user_id):
                    yield event
                return

        # Generate temporary session key for acquiring pool client
        # Use pending- prefix + timestamp to ensure uniqueness during initial session creation
        temp_session_key = generate_pending_session_id()
        pool_client = await self.client_pool.get_client(temp_session_key)

        # For resumed sessions: replace pool client with resume client
        if resume_session_id:
            from agent.core.agent_options import create_enhanced_options
            from claude_agent_sdk import ClaudeSDKClient

            logger.info(f"Replacing pool client {pool_client.index} with resume client for {resume_session_id[:20]}...")
            # Note: disconnect may raise "cancel scope" error if client was created in different task
            try:
                await pool_client.client.disconnect()
            except Exception as e:
                logger.warning(f"Failed to disconnect old pool client {pool_client.index}: {e}")
                # Continue anyway - the old client will be garbage collected

            resume_options = create_enhanced_options(resume_session_id=resume_session_id)
            resume_client = ClaudeSDKClient(options=resume_options)
            await resume_client.connect()

            # Replace the client in the pool
            pool_client.client = resume_client
            logger.info(f"Pool client {pool_client.index} now has resume session {resume_session_id[:20]}...")

        # Release the pool client lock immediately - we'll just use the client
        # The session lock will handle concurrency control for subsequent messages
        if pool_client.lock.locked():
            pool_client.lock.release()

        real_session_id = resume_session_id
        is_resuming = resume_session_id is not None
        history = get_history_storage()
        session_registered = False
        ctx = StreamingContext()
        logger.info(f"Creating session with pool client {pool_client.index} (resume={resume_session_id}, user={user_id})")

        try:
            await pool_client.client.query(content)

            async for msg in pool_client.client.receive_response():
                # Handle SystemMessage to capture real session ID from SDK
                # This is critical for linking our temporary session key to the actual SDK session
                if isinstance(msg, SystemMessage):
                    if msg.subtype == "init" and msg.data:
                        sdk_session_id = msg.data.get("session_id")
                        if sdk_session_id:
                            real_session_id = sdk_session_id
                            if not session_registered:
                                # For NEW sessions: use pending-xxx as key in SessionManager
                                # For RESUMED sessions: use real SDK ID as key
                                # This difference matters for how subsequent messages find the session
                                session_key = sdk_session_id if is_resuming else temp_session_key

                                session_state = await self.session_manager.register_session(
                                    session_key,
                                    pool_client.index,
                                    real_session_id=sdk_session_id,
                                    first_message=content,
                                    user_id=user_id
                                )
                                session_state.status = "active"
                                session_registered = True
                                # Save user message with REAL session ID for history persistence
                                history.append_message(sdk_session_id, "user", content)

                                # Update pool client's session_id to the real SDK ID
                                # This ensures subsequent requests can locate this client via the real ID
                                pool_client.current_session_id = sdk_session_id
                            try:
                                yield {"event": "session_id", "data": {"session_id": sdk_session_id}}
                            except GeneratorExit:
                                # Client disconnected during session_id event, continue consuming response
                                logger.info(f"Client disconnected after session_id for {real_session_id} in create_and_stream")
                                pass
                    continue

                # Process message and yield SSE events
                events = process_message(msg, ctx)
                try:
                    for event in events:
                        yield event
                except GeneratorExit:
                    # Client disconnected while yielding events
                    # Continue consuming the rest of the response to avoid SDK state corruption
                    logger.info(f"Client disconnected during streaming for {real_session_id} in create_and_stream")
                    pass

                # Save assistant response to history when we get the result
                if isinstance(msg, ResultMessage):
                    if real_session_id:
                        history.append_message(
                            real_session_id,
                            "assistant",
                            ctx.accumulated_text,
                            tool_use=ctx.tool_uses or None,
                            tool_results=ctx.tool_results or None,
                        )

        except Exception as e:
            logger.error(f"Error during create_and_stream with pool client {pool_client.index}, session {real_session_id}: {e}", exc_info=True)
            try:
                yield {"event": "error", "data": {"message": str(e), "session_id": real_session_id}}
            except GeneratorExit:
                pass  # Client already disconnected
            raise
        finally:
            # DON'T release the pool client - keep it assigned for follow-up messages
            # The pool client will be released when the session expires or is explicitly closed
            # Just mark the session as idle to signal completion of this request
            if session_registered and real_session_id:
                session = await self.session_manager.find_by_session_or_real_id(real_session_id)
                if session:
                    logger.debug(f"Marking session {real_session_id} as idle (was: {session.status}) in create_and_stream")
                    session.status = "idle"
                else:
                    logger.warning(f"Session {real_session_id} not found for idle update in create_and_stream")

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

        Uses pool clients from SessionManager for efficient session reuse.

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

        # Get pool client for this session
        pool_client = self.session_manager.get_pool_client(session_id)
        if pool_client:
            logger.info(f"Using pool client {pool_client.index} for send_message to {session_id[:20]}...")
            client = pool_client.client
        else:
            raise ValueError(f"Pool client not found for session {session_id}")

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

        Uses pool clients from SessionManager for efficient session reuse.
        Only creates a new client if the session is not in memory.

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
        logger.debug(f"stream_message called with session_id={session_id}, user_id={user_id}")

        # Check if session exists in SessionManager
        session = await self.session_manager.find_by_session_or_real_id(session_id)
        logger.debug(f"Session lookup result for {session_id[:20]}...: found={session is not None}")

        if session:
            logger.debug(f"Session details: key={session.session_id[:20]}..., real_id={session.real_session_id[:20] if session.real_session_id else None}..., status={session.status}, client_index={session.client_index}")

        history = get_history_storage()
        sdk_id_for_history = session.real_session_id if session and session.real_session_id else session_id
        ctx = StreamingContext()
        is_pending = session_id.startswith(PENDING_SESSION_PREFIX)
        session_registered = False

        if session:
            # Get pool client for this session
            pool_client = self.session_manager.get_pool_client(session.session_id)
            if not pool_client:
                raise ValueError(f"Pool client not found for session {session_id}")

            logger.info(f"Using pool client {pool_client.index} for session {session_id[:20]}...")
            client = pool_client.client

            # Use session lock for concurrency control - prevents parallel requests to same session
            try:
                async with asyncio.timeout(LOCK_TIMEOUT_SECONDS):
                    async with session.lock:
                        if session.status != "idle":
                            raise ValueError(f"Session {session_id} is busy (status={session.status})")

                        session.status = "active"

                        try:
                            await client.query(content)

                            async for msg in client.receive_response():
                                # Handle SystemMessage for pending sessions (first message after resume)
                                # Pending sessions don't have a real SDK ID yet, so we capture it here
                                if isinstance(msg, SystemMessage):
                                    if msg.subtype == "init" and msg.data and not session.real_session_id:
                                        sdk_session_id = msg.data.get("session_id")
                                        if sdk_session_id:
                                            # Update session state with real SDK ID now that we have it
                                            session.real_session_id = sdk_session_id
                                            session.first_message = content
                                            sdk_id_for_history = sdk_session_id
                                            # Persist to storage
                                            self.session_manager._storage.save_session(
                                                sdk_session_id,
                                                first_message=content,
                                                user_id=session.user_id,
                                            )
                                            logger.info(f"Updated pending session {session_id[:20]}... with real SDK ID: {sdk_session_id}")
                                            yield {"event": "session_id", "data": {"session_id": sdk_session_id}}
                                    continue

                                # Process message and generate SSE events
                                for event in process_message(msg, ctx):
                                    yield event

                                # Save conversation history when we receive the final ResultMessage
                                # This ensures we capture the complete assistant response including tool results
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
                            # Always return session to idle state, even if errors occur
                            session.status = "idle"

            except asyncio.TimeoutError:
                logger.error(f"Lock acquisition timeout for session {session_id[:20]}... (waited {LOCK_TIMEOUT_SECONDS}s)")
                yield {"event": "error", "data": {"message": "Session busy, please try again", "session_id": session_id}}
                return

        else:
            # Session not in memory, need to create/reconnect
            # For pending sessions: create a brand new session with the provided pending ID
            # For real SDK IDs: resume the session by acquiring a pool client and replaying context
            if is_pending:
                # Create a new session with the provided pending ID
                logger.info(f"Creating new session with pending ID {session_id[:20]}...")
                pool_client = await self.client_pool.get_client(session_id)

                # Release the pool client lock immediately - we only need the client, not the lock
                if pool_client.lock.locked():
                    pool_client.lock.release()

                history = get_history_storage()
                ctx = StreamingContext()
                sdk_session_id = None
                session_registered = False

                try:
                    await pool_client.client.query(content)

                    async for msg in pool_client.client.receive_response():
                        # Handle SystemMessage to capture real session ID from SDK
                        if isinstance(msg, SystemMessage):
                            if msg.subtype == "init" and msg.data:
                                sdk_session_id = msg.data.get("session_id")
                                if sdk_session_id:
                                    # Register the session with the pending ID as key in SessionManager
                                    # This allows subsequent requests to find this session before we know the real ID
                                    session_state = await self.session_manager.register_session(
                                        session_id,
                                        pool_client.index,
                                        real_session_id=sdk_session_id,
                                        first_message=content,
                                        user_id=user_id
                                    )
                                    session_state.status = "active"
                                    session_registered = True
                                    history.append_message(sdk_session_id, "user", content)

                                    # Update pool client's session_id to the real SDK ID
                                    # This ensures subsequent requests can locate this client via the real ID
                                    pool_client.current_session_id = sdk_session_id

                                    logger.info(f"Registered pending session {session_id[:20]}... with real SDK ID: {sdk_session_id}")
                                    yield {"event": "session_id", "data": {"session_id": sdk_session_id}}
                            continue

                        # Process message and yield SSE events
                        for event in process_message(msg, ctx):
                            yield event

                        # Save assistant response to history when we get the final ResultMessage
                        if isinstance(msg, ResultMessage):
                            if sdk_session_id:
                                history.append_message(
                                    sdk_session_id,
                                    "assistant",
                                    ctx.accumulated_text,
                                    tool_use=ctx.tool_uses or None,
                                    tool_results=ctx.tool_results or None,
                                )

                except Exception as e:
                    logger.error(f"Error creating session for pending ID {session_id[:20]}...: {e}", exc_info=True)
                    yield {"event": "error", "data": {"message": str(e), "session_id": session_id}}
                    raise
                finally:
                    # Mark session as idle when done to signal completion
                    registered_session = await self.session_manager.find_by_session_or_real_id(session_id)
                    if registered_session:
                        logger.debug(f"Marking pending session {session_id[:20]}... as idle (was: {registered_session.status}) in stream_message")
                        registered_session.status = "idle"

                yield {
                    "event": "done",
                    "data": {"session_id": sdk_session_id or session_id, "turn_count": ctx.turn_count},
                }
                return

            # Resume with real SDK ID - acquire pool client
            # This path handles sessions that expired from memory or are being resumed after server restart
            logger.info(f"Acquiring pool client for resumed session {session_id[:20]}...")
            pool_client = await self.client_pool.get_client(session_id)

            # Double-checked locking: verify session still doesn't exist
            # Another request might have created it while we were waiting for the pool client
            existing_session = await self.session_manager.find_by_session_or_real_id(session_id)
            if existing_session:
                logger.info(f"Session {session_id[:20]}... created by another request, reusing")
                await self.client_pool.release_client(session_id)
                async for event in self.stream_message(session_id, content, user_id):
                    yield event
                return

            try:
                await pool_client.client.query(content)

                async for msg in pool_client.client.receive_response():
                    # Handle SystemMessage for resumed sessions to verify SDK session ID
                    if isinstance(msg, SystemMessage):
                        if msg.subtype == "init" and msg.data:
                            sdk_session_id = msg.data.get("session_id")
                            if sdk_session_id:
                                sdk_id_for_history = sdk_session_id
                        continue

                    # Process message and generate SSE events
                    for event in process_message(msg, ctx):
                        yield event

                    # Save conversation history when we receive the final ResultMessage
                    if isinstance(msg, ResultMessage):
                        history.append_message(sdk_id_for_history, "user", content)
                        history.append_message(
                            sdk_id_for_history,
                            "assistant",
                            ctx.accumulated_text,
                            tool_use=ctx.tool_uses or None,
                            tool_results=ctx.tool_results or None,
                        )

                # Register the resumed session in SessionManager
                # This makes it available for subsequent requests without going through the resume path again
                if not session_registered:
                    session_state = await self.session_manager.register_session(
                        sdk_id_for_history,
                        pool_client.index,
                        real_session_id=sdk_id_for_history,
                        first_message=content,
                        user_id=user_id,
                    )
                    session_registered = True

            except Exception as e:
                logger.error(f"Error during query for resumed session {session_id[:20]}...: {e}", exc_info=True)
                yield {"event": "error", "data": {"message": str(e), "session_id": session_id}}
                raise
            finally:
                # Release pool client back to the pool
                # Resumed sessions don't keep the client assigned like new sessions do
                await self.client_pool.release_client(session_id)
                logger.info(f"Released pool client {pool_client.index} for resumed session {session_id[:20]}...")

                if session_registered:
                    new_session_state = await self.session_manager.find_by_session_or_real_id(sdk_id_for_history)
                    if new_session_state:
                        logger.debug(f"Marking resumed session {sdk_id_for_history[:20]}... as idle in stream_message")
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

        # Use pool client if available
        client = self.session_manager.get_pool_client(session_id)
        if client:
            logger.info(f"Interrupting pool client {session_state.client_index} for session {session_id[:20]}...")
            await client.interrupt()
        else:
            logger.warning(f"Pool client not found for session {session_id}, cannot interrupt")
            return False

        return True
