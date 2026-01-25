"""WebSocket endpoint for persistent multi-turn conversations.

This approach keeps the SDK client in a single async context for the entire
WebSocket connection lifetime, avoiding the cancel scope task mismatch issue.

Supports AskUserQuestion tool callbacks for interactive user input during
agent execution.
"""
import asyncio
import logging
import os
import secrets
import uuid
from typing import Any, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk.types import (
    ResultMessage,
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)

from agent.core.agent_options import create_agent_sdk_options
from agent.core.storage import get_storage, get_history_storage
from api.constants import EventType
from api.services.message_utils import message_to_dict
from api.services.history_tracker import HistoryTracker
from api.services.question_manager import get_question_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

# Default timeout for AskUserQuestion responses (in seconds)
ASK_USER_QUESTION_TIMEOUT = 60


@router.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
    agent_id: Optional[str] = None,
    session_id: Optional[str] = None,
    api_key: Optional[str] = None
):
    """WebSocket endpoint for persistent multi-turn conversations.

    The SDK client is created once and reused for all messages within
    the WebSocket connection, maintaining the same async context.

    Supports session resumption via the session_id query parameter.
    Supports AskUserQuestion tool callbacks for interactive user input.

    Protocol:
        Client sends: {"content": "user message"}
                      {"type": "user_answer", "question_id": "...", "answers": {...}}
        Server sends: {"type": "session_id", "session_id": "..."}
                      {"type": "text_delta", "text": "..."}
                      {"type": "tool_use", ...}
                      {"type": "tool_result", ...}
                      {"type": "ask_user_question", "question_id": "...", "questions": [...], "timeout": 60}
                      {"type": "done", "turn_count": N}
                      {"type": "error", "error": "..."}

    Query Parameters:
        agent_id: Optional agent ID to use
        session_id: Optional session ID to resume
        api_key: Optional API key for authentication
    """
    # Validate API key if configured
    required_api_key = os.getenv("API_KEY")
    if required_api_key and not secrets.compare_digest(api_key or "", required_api_key):
        logger.warning(
            f"WebSocket auth failed: client={websocket.client.host}, path={websocket.url.path}"
        )
        await websocket.close(code=4001, reason="Invalid or missing API key")
        return

    await websocket.accept()
    logger.info(f"WebSocket connected, agent_id={agent_id}, session_id={session_id}")

    session_storage = get_storage()
    history = get_history_storage()

    # Check if resuming an existing session
    existing_session = None
    resume_session_id = None
    if session_id:
        existing_session = session_storage.get_session(session_id)
        if existing_session:
            resume_session_id = existing_session.session_id
            logger.info(f"Resuming session: {resume_session_id}")
        else:
            # Session not found - send error and close
            await websocket.send_json({
                "type": EventType.ERROR,
                "error": f"Session '{session_id}' not found"
            })
            await websocket.close(code=4004, reason="Session not found")
            return

    # Get question manager for AskUserQuestion callbacks
    question_manager = get_question_manager()

    # Define can_use_tool callback for AskUserQuestion handling
    async def can_use_tool_callback(
        tool_name: str,
        tool_input: dict[str, Any],
        context: ToolPermissionContext
    ) -> PermissionResultAllow | PermissionResultDeny:
        """Handle AskUserQuestion tool by sending question to client and waiting for answer.

        Args:
            tool_name: Name of the tool being invoked.
            tool_input: Input parameters for the tool.
            context: Tool permission context from SDK.

        Returns:
            - PermissionResultAllow with updated_input for successful handling
            - PermissionResultDeny to deny tool use (on timeout or error)
        """
        if tool_name == "AskUserQuestion":
            question_id = str(uuid.uuid4())
            questions = tool_input.get("questions", [])

            logger.info(f"AskUserQuestion invoked: question_id={question_id}, questions={len(questions)}")

            # Send question event to client
            try:
                await websocket.send_json({
                    "type": EventType.ASK_USER_QUESTION,
                    "question_id": question_id,
                    "questions": questions,
                    "timeout": ASK_USER_QUESTION_TIMEOUT
                })
            except Exception as e:
                logger.error(f"Failed to send question to client: {e}")
                return PermissionResultDeny(message="Failed to send question to client")

            # Register question and wait for answer
            question_manager.create_question(question_id, questions)
            try:
                answers = await question_manager.wait_for_answer(
                    question_id,
                    timeout=ASK_USER_QUESTION_TIMEOUT
                )
                logger.info(f"Received answers for question_id={question_id}")
                return PermissionResultAllow(updated_input={
                    "questions": questions,
                    "answers": answers
                })
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for answer: question_id={question_id}")
                return PermissionResultDeny(message="Timeout waiting for user response")
            except KeyError as e:
                logger.error(f"Question not found: {e}")
                return PermissionResultDeny(message=f"Question not found: {e}")
            except Exception as e:
                logger.error(f"Error waiting for answer: {e}")
                return PermissionResultDeny(message=f"Error: {e}")

        # Allow all other tools to execute normally
        return PermissionResultAllow(updated_input=tool_input)

    # Create SDK client with resume option and can_use_tool callback
    options = create_agent_sdk_options(
        agent_id=agent_id,
        resume_session_id=resume_session_id,
        can_use_tool=can_use_tool_callback
    )
    client = ClaudeSDKClient(options)

    # Initialize state from existing session or defaults
    sdk_session_id = resume_session_id
    turn_count = existing_session.turn_count if existing_session else 0
    first_message = existing_session.first_message if existing_session else None
    tracker = None  # Will be initialized once we have session_id

    try:
        # Connect SDK client
        try:
            await client.connect()
        except Exception as e:
            logger.error(f"Failed to connect SDK client: {e}", exc_info=True)
            await websocket.send_json({
                "type": EventType.ERROR,
                "error": f"Failed to initialize agent: {str(e)}"
            })
            await websocket.close(code=4002, reason="SDK client connection failed")
            return

        # Send ready signal with resume info if applicable
        ready_data = {"type": EventType.READY}
        if resume_session_id:
            ready_data["session_id"] = resume_session_id
            ready_data["resumed"] = True
            ready_data["turn_count"] = turn_count
        await websocket.send_json(ready_data)

        # For resumed sessions, initialize tracker immediately
        if resume_session_id:
            tracker = HistoryTracker(
                session_id=resume_session_id,
                history=history
            )

        # Queue for incoming messages that aren't user_answer
        message_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        # Flag to signal when we're processing a response (agent is active)
        processing_response = False

        async def receive_messages():
            """Background task to receive and route WebSocket messages.

            Routes user_answer messages directly to the question manager,
            and queues other messages for the main processing loop.
            """
            nonlocal processing_response
            try:
                while True:
                    data = await websocket.receive_json()
                    msg_type = data.get("type")

                    # Handle user_answer messages immediately (for AskUserQuestion)
                    if msg_type == EventType.USER_ANSWER:
                        question_id = data.get("question_id")
                        answers = data.get("answers", {})
                        if question_id:
                            logger.info(f"Received user_answer for question_id={question_id}")
                            question_manager.submit_answer(question_id, answers)
                        else:
                            logger.warning("Received user_answer without question_id")
                        continue

                    # Queue other messages for main loop processing
                    await message_queue.put(data)
            except WebSocketDisconnect:
                # Signal main loop to exit by putting None
                await message_queue.put(None)
                raise
            except Exception as e:
                logger.error(f"Error in receive_messages: {e}")
                await message_queue.put(None)
                raise

        # Start message receiver task
        receiver_task = asyncio.create_task(receive_messages())

        try:
            while True:
                # Wait for message from queue
                data = await message_queue.get()

                # None signals disconnect
                if data is None:
                    break

                content = data.get("content", "")

                if not content:
                    await websocket.send_json({"type": EventType.ERROR, "error": "Empty content"})
                    continue

                # Track first message for session metadata
                if first_message is None:
                    first_message = content[:100]  # Truncate for storage

                # Save user message immediately if we already have session_id (follow-up turns)
                # Otherwise queue it to save after we receive the session_id event
                if tracker:
                    tracker.save_user_message(content)
                    pending_user_message = None
                else:
                    pending_user_message = content

                try:
                    # Mark that we're processing a response
                    processing_response = True

                    # Send query (same client, same async context!)
                    await client.query(content)

                    # Stream responses
                    async for msg in client.receive_response():
                        event_data = message_to_dict(msg)

                        if event_data:
                            event_type = event_data.get("type")

                            # Capture session_id and initialize tracker
                            if event_type == EventType.SESSION_ID:
                                sdk_session_id = event_data["session_id"]

                                # Initialize history tracker if not already done (new session)
                                if tracker is None:
                                    tracker = HistoryTracker(
                                        session_id=sdk_session_id,
                                        history=history
                                    )
                                    # Save session to sessions.json (only for new sessions)
                                    session_storage.save_session(
                                        session_id=sdk_session_id,
                                        first_message=first_message
                                    )

                                # Save the pending user message (first turn only)
                                if pending_user_message:
                                    tracker.save_user_message(pending_user_message)

                            # Process event through history tracker (if initialized)
                            elif tracker:
                                tracker.process_event(event_type, event_data)

                            # Send to client
                            await websocket.send_json(event_data)

                        # Break on ResultMessage
                        if isinstance(msg, ResultMessage):
                            break

                    turn_count += 1
                    processing_response = False

                    # Finalize assistant response (handles accumulated text)
                    if tracker:
                        tracker.finalize_assistant_response()

                    # Update turn count in session storage
                    if sdk_session_id:
                        session_storage.update_session(
                            session_id=sdk_session_id,
                            turn_count=turn_count
                        )

                except Exception as e:
                    processing_response = False
                    logger.error(f"Error processing message: {e}", exc_info=True)

                    # Save any accumulated text before error
                    if tracker and tracker.has_accumulated_text():
                        tracker.finalize_assistant_response(metadata={"error": str(e)})

                    await websocket.send_json({"type": EventType.ERROR, "error": str(e)})
        finally:
            # Cancel the receiver task
            receiver_task.cancel()
            try:
                await receiver_task
            except asyncio.CancelledError:
                pass

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected, session={sdk_session_id}, turns={turn_count}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        # Cleanup - disconnect SDK client
        try:
            await client.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting SDK client: {e}")
