"""Platform message processing worker.

Handles the full lifecycle of a platform message:
1. Resolve platform identity to internal username
2. Get or create a session
3. Invoke the Claude agent
4. Accumulate response and send back via platform adapter
"""

import logging
import os

from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk.types import AssistantMessage, ResultMessage, TextBlock, UserMessage

from agent.core.agent_options import create_agent_sdk_options, set_email_tools_username
from agent.core.storage import get_user_history_storage, get_user_session_storage
from api.constants import FIRST_MESSAGE_TRUNCATE_LENGTH, TOOL_REF_PATTERN
from api.services.history_tracker import HistoryTracker
from api.services.message_utils import message_to_dicts
from api.services.streaming_input import create_message_generator
from platforms.base import NormalizedMessage, NormalizedResponse, PlatformAdapter
from platforms.identity import platform_identity_to_username
from platforms.session_bridge import get_session_id_for_chat, save_session_mapping

logger = logging.getLogger(__name__)

# Default agent ID for platform messages — read from env var
DEFAULT_PLATFORM_AGENT_ID: str | None = os.getenv("PLATFORM_DEFAULT_AGENT_ID")


async def process_platform_message(
    msg: NormalizedMessage,
    adapter: PlatformAdapter,
    agent_id: str | None = None,
) -> None:
    """Process an inbound platform message through the agent pipeline.

    This is the main entry point called by the webhook router's background task.

    Args:
        msg: Normalized inbound message from the platform.
        adapter: The platform adapter to use for sending the response.
        agent_id: Optional agent ID override. Falls back to DEFAULT_PLATFORM_AGENT_ID.
    """
    effective_agent_id = agent_id or DEFAULT_PLATFORM_AGENT_ID

    try:
        # Send typing indicator while we process (non-critical)
        try:
            await adapter.send_typing_indicator(msg.platform_chat_id)
        except Exception as e:
            logger.debug(f"Failed to send typing indicator: {e}")

        # Resolve identity
        username = platform_identity_to_username(msg.platform, msg.platform_user_id)
        logger.info(
            f"Processing {msg.platform} message: user={username}, "
            f"chat={msg.platform_chat_id}"
        )

        # Get storage
        session_storage = get_user_session_storage(username)
        history_storage = get_user_history_storage(username)

        # Look up or create session
        session_id = get_session_id_for_chat(username, msg.platform_chat_id)
        resume_session_id = session_id

        if session_id:
            existing = session_storage.get_session(session_id)
            if existing:
                turn_count = existing.turn_count
            else:
                # Session mapping exists but session was deleted — start fresh
                session_id = None
                resume_session_id = None
                turn_count = 0
        else:
            turn_count = 0

        # Set email tools username context
        set_email_tools_username(username)

        # Build SDK options
        options = create_agent_sdk_options(
            agent_id=effective_agent_id,
            resume_session_id=resume_session_id,
        )
        client = ClaudeSDKClient(options)

        try:
            await client.connect()

            # Create tracker (or defer until session_id is known)
            tracker: HistoryTracker | None = None
            if resume_session_id:
                tracker = HistoryTracker(
                    session_id=resume_session_id, history=history_storage
                )
                tracker.save_user_message(msg.text)

            # Build first_message preview
            first_message = msg.text[:FIRST_MESSAGE_TRUNCATE_LENGTH] if msg.text else None

            # Send user message to agent
            message_gen = create_message_generator(
                msg.text, session_id or "default"
            )
            await client.query(message_gen, session_id=session_id or "default")

            # Process response stream and accumulate text
            response_text = ""
            new_session_id: str | None = session_id

            async for sdk_msg in client.receive_response():
                if isinstance(sdk_msg, AssistantMessage):
                    if tracker:
                        tracker.save_from_assistant_message(sdk_msg)
                    for block in sdk_msg.content:
                        if isinstance(block, TextBlock) and block.text.strip():
                            cleaned = TOOL_REF_PATTERN.sub("", block.text).strip()
                            if cleaned:
                                if response_text:
                                    response_text += "\n\n"
                                response_text += cleaned

                elif isinstance(sdk_msg, UserMessage):
                    if tracker:
                        tracker.save_from_user_message(sdk_msg)

                elif isinstance(sdk_msg, ResultMessage):
                    # Check for session_id in result
                    result_session_id = getattr(sdk_msg, "session_id", None)
                    if result_session_id and not new_session_id:
                        new_session_id = result_session_id
                    break

                else:
                    # Handle StreamEvent-like messages that carry session_id
                    events = message_to_dicts(sdk_msg)
                    for event_data in events:
                        event_type = event_data.get("type")
                        if event_type == "session_id":
                            new_session_id = event_data.get("session_id")
                            if new_session_id and not tracker:
                                tracker = HistoryTracker(
                                    session_id=new_session_id,
                                    history=history_storage,
                                )
                                # Save session
                                session_storage.save_session(
                                    session_id=new_session_id,
                                    first_message=first_message,
                                    user_id=username,
                                    agent_id=effective_agent_id,
                                )
                                # Save the user message now
                                tracker.save_user_message(msg.text)
                                # Persist chat → session mapping
                                save_session_mapping(
                                    username, msg.platform_chat_id, new_session_id
                                )
                        elif event_type and tracker:
                            tracker.process_event(event_type, event_data)
                            # Accumulate text from text_delta events
                            if event_type == "text_delta":
                                response_text += event_data.get("text", "")

            # Finalize tracker
            if tracker:
                tracker.finalize_assistant_response()

            # Update turn count
            turn_count += 1
            if new_session_id:
                session_storage.update_session(
                    session_id=new_session_id, turn_count=turn_count
                )
                # Ensure mapping is saved for new sessions
                if not session_id and new_session_id:
                    save_session_mapping(
                        username, msg.platform_chat_id, new_session_id
                    )

            # Send response back to platform
            if response_text:
                response = NormalizedResponse(text=response_text)
                await adapter.send_response(msg.platform_chat_id, response)
            else:
                await adapter.send_response(
                    msg.platform_chat_id,
                    NormalizedResponse(text="(No response generated)"),
                )

        finally:
            try:
                await client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting SDK client: {e}")

    except Exception as e:
        logger.error(
            f"Error processing platform message: {e}",
            exc_info=True,
        )
        # Try to send error response to user
        try:
            await adapter.send_response(
                msg.platform_chat_id,
                NormalizedResponse(
                    text="Sorry, I encountered an error processing your message. Please try again."
                ),
            )
        except Exception:
            logger.error("Failed to send error response to platform", exc_info=True)
