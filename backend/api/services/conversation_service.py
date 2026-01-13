"""Conversation service for handling Claude SDK interactions."""

from typing import AsyncIterator, Any, Optional

from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk.types import (
    Message,
    StreamEvent,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock
)

from agent.core.agent_options import create_enhanced_options
from api.services.session_manager import SessionManager


class ConversationService:
    """Service for handling conversation logic with Claude SDK."""

    def __init__(self, session_manager: SessionManager):
        """Initialize conversation service.

        Args:
            session_manager: SessionManager instance for managing sessions
        """
        self.session_manager = session_manager

    async def create_and_stream(
        self,
        content: str,
        resume_session_id: Optional[str] = None,
        agent_id: Optional[str] = None
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
        # Create client and initialize with connect()
        options = create_enhanced_options(resume_session_id=resume_session_id, agent_id=agent_id)
        client = ClaudeSDKClient(options)
        await client.connect()

        real_session_id = resume_session_id

        # Send query directly on client
        await client.query(content)

        # Stream response
        turn_count = 0
        session_registered = False
        async for msg in client.receive_response():
            # Handle SystemMessage to capture real session ID
            if isinstance(msg, SystemMessage):
                if msg.subtype == "init" and msg.data:
                    sdk_session_id = msg.data.get("session_id")
                    if sdk_session_id:
                        real_session_id = sdk_session_id
                        # Register session IMMEDIATELY so it's available for subsequent requests
                        if not session_registered:
                            await self.session_manager.register_session(real_session_id, client, content)
                            session_registered = True
                        yield {
                            "event": "session_id",
                            "data": {"session_id": sdk_session_id}
                        }
                continue

            # Handle StreamEvent for text deltas
            if isinstance(msg, StreamEvent):
                event = msg.event
                if event.get("type") == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        if text:
                            yield {
                                "event": "text_delta",
                                "data": {"text": text}
                            }

            # Handle AssistantMessage for tool use
            elif isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, ToolUseBlock):
                        yield {
                            "event": "tool_use",
                            "data": {
                                "tool_name": block.name,
                                "input": block.input if block.input else {}
                            }
                        }

            # Handle UserMessage for tool results
            elif isinstance(msg, UserMessage):
                for block in msg.content:
                    if isinstance(block, ToolResultBlock):
                        tool_content = block.content
                        if tool_content is None:
                            tool_content = ""
                        elif not isinstance(tool_content, str):
                            if isinstance(tool_content, list):
                                tool_content = "\n".join(str(item) for item in tool_content)
                            else:
                                tool_content = str(tool_content)

                        yield {
                            "event": "tool_result",
                            "data": {
                                "tool_use_id": block.tool_use_id,
                                "content": tool_content,
                                "is_error": block.is_error if hasattr(block, 'is_error') else False
                            }
                        }

            # Handle ResultMessage for completion
            elif isinstance(msg, ResultMessage):
                turn_count = msg.num_turns

        # Send done event
        yield {
            "event": "done",
            "data": {
                "session_id": real_session_id,
                "turn_count": turn_count
            }
        }

    def _convert_message(self, msg: Message) -> dict[str, Any]:
        """Convert SDK message types to API format.

        Args:
            msg: SDK Message object

        Returns:
            Dictionary representation of the message
        """
        result: dict[str, Any] = {
            "type": msg.__class__.__name__
        }

        if isinstance(msg, SystemMessage):
            result.update({
                "subtype": msg.subtype,
                "data": msg.data
            })

        elif isinstance(msg, UserMessage):
            content_list = []
            for block in msg.content:
                if isinstance(block, TextBlock):
                    content_list.append({
                        "type": "text",
                        "text": block.text
                    })
                elif isinstance(block, ToolResultBlock):
                    content_list.append({
                        "type": "tool_result",
                        "tool_use_id": block.tool_use_id,
                        "content": block.content
                    })
            result["content"] = content_list

        elif isinstance(msg, AssistantMessage):
            content_list = []
            for block in msg.content:
                if isinstance(block, TextBlock):
                    content_list.append({
                        "type": "text",
                        "text": block.text
                    })
                elif isinstance(block, ToolUseBlock):
                    content_list.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })
            result["content"] = content_list

        elif isinstance(msg, ResultMessage):
            result.update({
                "subtype": msg.subtype,
                "num_turns": msg.num_turns,
                "total_cost_usd": msg.total_cost_usd
            })

        elif isinstance(msg, StreamEvent):
            result["event"] = msg.event

        return result

    async def send_message(
        self,
        session_id: str,
        content: str
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
        # Get session with persistent client
        session = await self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        client = session.client

        # Send query on persistent client (no reconnection)
        await client.query(content)

        # Collect all messages
        messages = []
        response_text = ""
        tool_uses = []
        turn_count = 0

        async for msg in client.receive_response():
            # Skip SystemMessage
            if isinstance(msg, SystemMessage):
                continue

            messages.append(self._convert_message(msg))

            # Extract text from AssistantMessage
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        response_text += block.text
                    elif isinstance(block, ToolUseBlock):
                        tool_uses.append({
                            "name": block.name,
                            "input": block.input
                        })

            # Get turn count from ResultMessage
            if isinstance(msg, ResultMessage):
                turn_count = msg.num_turns

        # Client persists - no disconnect
        return {
            "session_id": session_id,
            "response": response_text,
            "tool_uses": tool_uses,
            "turn_count": turn_count,
            "messages": messages
        }

    async def stream_message(
        self,
        session_id: str,
        content: str
    ) -> AsyncIterator[dict[str, Any]]:
        """Send a message to an existing session and stream the response.

        Creates a fresh client with resume_session_id to continue the conversation.
        The Claude SDK requires a new client connection for each query.

        Args:
            session_id: Session ID to continue
            content: User message content

        Yields:
            SSE-formatted event dictionaries

        Raises:
            ValueError: If session not found in history
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[stream_message] Called with session_id={session_id}, content={content[:50]}...")

        # Verify session exists (in memory or history)
        session = await self.session_manager.get_session(session_id)
        if not session:
            # Check if it exists in history
            history = self.session_manager.get_session_history()
            if session_id not in history:
                logger.error(f"[stream_message] Session {session_id} NOT FOUND")
                raise ValueError(f"Session {session_id} not found")

        logger.info(f"[stream_message] Session found, creating fresh client with resume_session_id...")

        # Create a fresh client with resume_session_id to continue the conversation
        # The SDK requires a new connection for each query after the first completes
        options = create_enhanced_options(resume_session_id=session_id)
        client = ClaudeSDKClient(options)
        await client.connect()

        logger.info(f"[stream_message] Fresh client connected, sending query...")
        await client.query(content)
        logger.info(f"[stream_message] Query sent, starting response iteration...")

        # Stream response
        turn_count = 0
        total_cost = 0.0
        msg_count = 0
        async for msg in client.receive_response():
            msg_count += 1
            logger.info(f"[stream_message] Received message #{msg_count}: {type(msg).__name__}")
            # Skip SystemMessage for resumed sessions (we already have the session_id)
            if isinstance(msg, SystemMessage):
                continue

            # Handle StreamEvent for text deltas
            if isinstance(msg, StreamEvent):
                event = msg.event
                if event.get("type") == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        if text:
                            yield {
                                "event": "text_delta",
                                "data": {"text": text}
                            }

            # Handle AssistantMessage for tool use
            elif isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, ToolUseBlock):
                        yield {
                            "event": "tool_use",
                            "data": {
                                "tool_name": block.name,
                                "input": block.input if block.input else {}
                            }
                        }

            # Handle UserMessage for tool results
            elif isinstance(msg, UserMessage):
                for block in msg.content:
                    if isinstance(block, ToolResultBlock):
                        tool_content = block.content
                        if tool_content is None:
                            tool_content = ""
                        elif not isinstance(tool_content, str):
                            if isinstance(tool_content, list):
                                tool_content = "\n".join(str(item) for item in tool_content)
                            else:
                                tool_content = str(tool_content)

                        yield {
                            "event": "tool_result",
                            "data": {
                                "tool_use_id": block.tool_use_id,
                                "content": tool_content,
                                "is_error": block.is_error if hasattr(block, 'is_error') else False
                            }
                        }

            # Handle ResultMessage for completion
            elif isinstance(msg, ResultMessage):
                turn_count = msg.num_turns
                total_cost = msg.total_cost_usd

        # Send done event
        yield {
            "event": "done",
            "data": {
                "session_id": session_id,
                "turn_count": turn_count,
                "total_cost_usd": total_cost
            }
        }

        # Cleanup - disconnect this client since we create fresh ones for each query
        try:
            await client.disconnect()
        except Exception:
            pass

    async def interrupt(self, session_id: str) -> bool:
        """Interrupt the current task for a session.

        Args:
            session_id: Session ID

        Returns:
            True if interrupted successfully, False if session not found

        Raises:
            ValueError: If session not found
        """
        session_state = await self.session_manager.get_session(session_id)
        if not session_state:
            raise ValueError(f"Session {session_id} not found")

        await session_state.client.interrupt()
        return True
