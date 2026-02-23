"""Conversation management endpoints with SSE streaming."""
import json
import logging
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from agent.core.agent_options import set_email_tools_username, set_media_tools_username
from agent.core.storage import get_user_history_storage
from api.constants import EventType
from api.dependencies import SessionManagerDep
from api.dependencies.auth import get_current_user
from api.models.requests import SendMessageRequest, CreateConversationRequest
from api.models.user_auth import UserTokenPayload
from api.services.history_tracker import HistoryTracker
from api.services.message_utils import convert_messages_to_sse
from api.utils.sensitive_data_filter import sanitize_paths

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("")
async def create_conversation(
    request: CreateConversationRequest,
    manager: SessionManagerDep,
    user: UserTokenPayload = Depends(get_current_user)
):
    """Create a new conversation and stream the response via SSE."""
    session_id = request.session_id or str(uuid.uuid4())

    return EventSourceResponse(
        _stream_conversation_events(session_id, request.content, manager, request.agent_id, user.username),
        media_type="text/event-stream"
    )


async def _stream_conversation_events(
    session_id: str,
    content: str,
    manager,
    agent_id: str | None = None,
    username: str | None = None
) -> AsyncIterator[dict]:
    """Async generator that streams conversation events as SSE."""
    if username:
        set_email_tools_username(username)
        set_media_tools_username(username)

    session, resolved_id, found_in_cache = await manager.get_or_create_conversation_session(
        session_id, agent_id
    )

    tracker = HistoryTracker(
        session_id=resolved_id,
        history=get_user_history_storage(username) if username else None
    )

    yield {
        "event": EventType.SESSION_ID,
        "data": json.dumps({
            "session_id": resolved_id,
            "found_in_cache": found_in_cache
        })
    }

    pending_id = resolved_id
    tracker.save_user_message(content)

    try:
        async for msg in session.send_query(content):
            sse_events = convert_messages_to_sse(msg)

            for sse_event in sse_events:
                event_type = sse_event.get("event")

                try:
                    data = json.loads(sse_event.get("data", "{}"))
                except json.JSONDecodeError:
                    data = {}

                if event_type == EventType.SESSION_ID and "session_id" in data:
                    sdk_sid = data["session_id"]
                    session.sdk_session_id = sdk_sid  # Store for multi-turn context
                    manager.register_sdk_session_id(pending_id, sdk_sid)
                    yield {
                        "event": "sdk_session_id",
                        "data": json.dumps({"sdk_session_id": sdk_sid})
                    }
                    continue

                tracker.process_event(event_type, data)

                raw_data = sse_event.get("data", "")
                if isinstance(raw_data, str):
                    sse_event["data"] = sanitize_paths(raw_data)

                yield sse_event

    except Exception as e:
        logger.error(f"Error streaming conversation for session {resolved_id}: {e}", exc_info=True)
        if tracker.has_accumulated_text():
            tracker.finalize_assistant_response(metadata={"error": str(e)})

        yield {
            "event": EventType.ERROR,
            "data": json.dumps({"error": str(e), "type": type(e).__name__})
        }


@router.post("/{session_id}/stream")
async def stream_conversation(
    session_id: str,
    request: SendMessageRequest,
    manager: SessionManagerDep,
    user: UserTokenPayload = Depends(get_current_user)
):
    """Send a message and stream the response via SSE."""
    return EventSourceResponse(
        _stream_conversation_events(session_id, request.content, manager, username=user.username),
        media_type="text/event-stream"
    )
