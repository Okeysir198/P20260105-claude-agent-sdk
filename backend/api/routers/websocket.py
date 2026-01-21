"""WebSocket endpoint for persistent multi-turn conversations.

This approach keeps the SDK client in a single async context for the entire
WebSocket connection lifetime, avoiding the cancel scope task mismatch issue.
"""
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk.types import ResultMessage

from agent.core.agent_options import create_agent_sdk_options
from agent.core.storage import get_storage, get_history_storage
from api.constants import EventType
from api.services.message_utils import message_to_dict
from api.services.history_tracker import HistoryTracker

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
    agent_id: Optional[str] = None,
    session_id: Optional[str] = None
):
    """WebSocket endpoint for persistent multi-turn conversations.

    The SDK client is created once and reused for all messages within
    the WebSocket connection, maintaining the same async context.

    Supports session resumption via the session_id query parameter.

    Protocol:
        Client sends: {"content": "user message"}
        Server sends: {"type": "session_id", "session_id": "..."}
                      {"type": "text_delta", "text": "..."}
                      {"type": "tool_use", ...}
                      {"type": "tool_result", ...}
                      {"type": "done", "turn_count": N}
                      {"type": "error", "error": "..."}

    Query Parameters:
        agent_id: Optional agent ID to use
        session_id: Optional session ID to resume
    """
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

    # Create SDK client with resume option if applicable
    options = create_agent_sdk_options(
        agent_id=agent_id,
        resume_session_id=resume_session_id
    )
    client = ClaudeSDKClient(options)

    # Initialize state from existing session or defaults
    sdk_session_id = resume_session_id
    turn_count = existing_session.turn_count if existing_session else 0
    first_message = existing_session.first_message if existing_session else None
    tracker = None  # Will be initialized once we have session_id

    try:
        # Connect SDK client
        await client.connect()

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

        while True:
            # Wait for message from client
            data = await websocket.receive_json()
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
                logger.error(f"Error processing message: {e}", exc_info=True)

                # Save any accumulated text before error
                if tracker and tracker.has_accumulated_text():
                    tracker.finalize_assistant_response(metadata={"error": str(e)})

                await websocket.send_json({"type": EventType.ERROR, "error": str(e)})

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
