"""WebSocket endpoint for persistent multi-turn conversations.

This approach keeps the SDK client in a single async context for the entire
WebSocket connection lifetime, avoiding the cancel scope task mismatch issue.

Supports AskUserQuestion tool callbacks for interactive user input during
agent execution.
Requires JWT token authentication.
"""
import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk.types import (
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    ToolPermissionContext,
)

from agent.core.agent_options import create_agent_sdk_options
from agent.core.storage import get_user_history_storage, get_user_session_storage
from api.constants import (
    ASK_USER_QUESTION_TIMEOUT,
    FIRST_MESSAGE_TRUNCATE_LENGTH,
    EventType,
    WSCloseCode,
)
from api.middleware.jwt_auth import validate_websocket_token
from api.services.history_tracker import HistoryTracker
from api.services.message_utils import message_to_dicts
from api.services.question_manager import QuestionManager, get_question_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@dataclass
class WebSocketState:
    """Mutable state for a WebSocket chat session."""

    session_id: str | None = None
    turn_count: int = 0
    first_message: str | None = None
    tracker: HistoryTracker | None = None
    pending_user_message: str | None = None
    last_ask_user_question_tool_use_id: str | None = None


class AskUserQuestionHandler:
    """Handles AskUserQuestion tool callbacks for WebSocket sessions."""

    def __init__(
        self,
        websocket: WebSocket,
        question_manager: QuestionManager,
        state: "WebSocketState",
        timeout: int = ASK_USER_QUESTION_TIMEOUT
    ):
        self._websocket = websocket
        self._question_manager = question_manager
        self._state = state
        self._timeout = timeout

    async def handle(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        context: ToolPermissionContext
    ) -> PermissionResultAllow | PermissionResultDeny:
        """Handle tool permission requests.

        For AskUserQuestion, sends question to client and waits for answer.
        All other tools are allowed to proceed.
        """
        if tool_name != "AskUserQuestion":
            return PermissionResultAllow(updated_input=tool_input)

        # Use the tool_use_id from the streamed event (stored in state), or generate a new UUID as fallback
        question_id = self._state.last_ask_user_question_tool_use_id or str(uuid.uuid4())
        questions = tool_input.get("questions", [])
        logger.info(f"AskUserQuestion invoked: question_id={question_id}, questions={len(questions)}")

        if not await self._send_question(question_id, questions):
            return PermissionResultDeny(message="Failed to send question to client")

        return await self._wait_for_answer(question_id, questions)

    async def _send_question(self, question_id: str, questions: list) -> bool:
        """Send question event to client. Returns True on success."""
        try:
            await self._websocket.send_json({
                "type": EventType.ASK_USER_QUESTION,
                "question_id": question_id,
                "questions": questions,
                "timeout": self._timeout
            })
            return True
        except Exception as e:
            logger.error(f"Failed to send question to client: {e}")
            return False

    async def _wait_for_answer(
        self,
        question_id: str,
        questions: list
    ) -> PermissionResultAllow | PermissionResultDeny:
        """Wait for user answer with timeout handling."""
        self._question_manager.create_question(question_id, questions)

        try:
            answers = await self._question_manager.wait_for_answer(question_id, timeout=self._timeout)
            logger.info(f"Received answers for question_id={question_id}")
            return PermissionResultAllow(updated_input={"questions": questions, "answers": answers})
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for answer: question_id={question_id}")
            return PermissionResultDeny(message="Timeout waiting for user response")
        except KeyError as e:
            logger.error(f"Question not found: {e}")
            return PermissionResultDeny(message=f"Question not found: {e}")
        except Exception as e:
            logger.error(f"Error waiting for answer: {e}")
            return PermissionResultDeny(message=f"Error: {e}")


async def _validate_websocket_auth(
    websocket: WebSocket,
    token: str | None = None
) -> tuple[str, str, str]:
    """Validate WebSocket authentication via JWT token.

    Returns:
        Tuple of (user_id, jti, username) if authenticated, closes WebSocket and raises WebSocketDisconnect if not.

    Args:
        websocket: The WebSocket connection
        token: JWT token from query parameter
    """
    user_id, jti = await validate_websocket_token(websocket, token)

    # Extract username from token
    from api.services.token_service import token_service
    username = ""
    if token_service and token:
        # Try user_identity type first, then access type
        payload = token_service.decode_and_validate_token(token, token_type="user_identity")
        if not payload:
            payload = token_service.decode_and_validate_token(token, token_type="access")
        username = payload.get("username", "") if payload else ""

    if not username:
        await websocket.close(code=WSCloseCode.AUTH_FAILED, reason="Token missing username")
        raise WebSocketDisconnect(code=WSCloseCode.AUTH_FAILED)

    return user_id, jti, username


class SessionResolutionError(Exception):
    """Raised when session resolution fails."""


async def _resolve_session(
    websocket: WebSocket,
    session_id: str | None,
    session_storage: Any
) -> tuple[Any | None, str | None]:
    """Resolve existing session or return None for new session.

    Returns:
        Tuple of (existing_session, resume_session_id). Both None for new sessions.

    Raises:
        SessionResolutionError: If session lookup failed and connection was closed.
    """
    if not session_id:
        return None, None

    existing_session = session_storage.get_session(session_id)
    if existing_session:
        logger.info(f"Resuming session: {existing_session.session_id}")
        return existing_session, existing_session.session_id

    await websocket.send_json({"type": EventType.ERROR, "error": f"Session '{session_id}' not found"})
    await websocket.close(code=WSCloseCode.SESSION_NOT_FOUND, reason="Session not found")
    raise SessionResolutionError(f"Session '{session_id}' not found")


class SDKConnectionError(Exception):
    """Raised when SDK client connection fails."""


async def _connect_sdk_client(websocket: WebSocket, client: ClaudeSDKClient) -> None:
    """Connect SDK client.

    Raises:
        SDKConnectionError: If connection failed and WebSocket was closed.
    """
    try:
        await client.connect()
    except Exception as e:
        logger.error(f"Failed to connect SDK client: {e}", exc_info=True)
        await websocket.send_json({"type": EventType.ERROR, "error": f"Failed to initialize agent: {str(e)}"})
        await websocket.close(code=WSCloseCode.SDK_CONNECTION_FAILED, reason="SDK client connection failed")
        raise SDKConnectionError(str(e)) from e


def _build_ready_message(resume_session_id: str | None, turn_count: int) -> dict[str, Any]:
    """Build the ready message payload."""
    ready_data: dict[str, Any] = {"type": EventType.READY}
    if resume_session_id:
        ready_data["session_id"] = resume_session_id
        ready_data["resumed"] = True
        ready_data["turn_count"] = turn_count
    return ready_data


async def _create_message_receiver(
    websocket: WebSocket,
    message_queue: asyncio.Queue,
    question_manager: QuestionManager,
    state: WebSocketState
) -> None:
    """Background task to receive and route WebSocket messages.

    Routes user_answer messages directly to the question manager,
    and queues other messages for the main processing loop.
    """
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == EventType.USER_ANSWER:
                question_id = data.get("question_id")
                if question_id:
                    logger.info(f"Received user_answer for question_id={question_id}")
                    # Save to history before submitting
                    if state.tracker:
                        state.tracker.process_event(EventType.USER_ANSWER, data)
                    question_manager.submit_answer(question_id, data.get("answers", {}))
                else:
                    logger.warning("Received user_answer without question_id")
                continue

            await message_queue.put(data)
    except WebSocketDisconnect:
        await message_queue.put(None)
        raise
    except Exception as e:
        logger.error(f"Error in receive_messages: {e}")
        await message_queue.put(None)
        raise


async def _process_response_stream(
    client: ClaudeSDKClient,
    websocket: WebSocket,
    state: WebSocketState,
    session_storage: Any,
    history: Any,
    agent_id: str | None = None
) -> None:
    """Process the response stream from the SDK client."""
    async for msg in client.receive_response():
        # Use message_to_dicts to get all events (handles UserMessage with multiple tool_results)
        events = message_to_dicts(msg)

        for event_data in events:
            event_type = event_data.get("type")

            # Capture tool_use_id for AskUserQuestion to use as question_id
            if event_type == EventType.TOOL_USE and event_data.get("name") == "AskUserQuestion":
                state.last_ask_user_question_tool_use_id = event_data.get("id")

            if event_type == EventType.SESSION_ID:
                _handle_session_id_event(event_data, state, session_storage, history, agent_id=agent_id)
            elif state.tracker:
                state.tracker.process_event(event_type, event_data)

            await websocket.send_json(event_data)

        if isinstance(msg, ResultMessage):
            break


def _handle_session_id_event(
    event_data: dict[str, Any],
    state: WebSocketState,
    session_storage: Any,
    history: Any,
    agent_id: str | None = None
) -> None:
    """Handle session_id event - initialize tracker and save pending message."""
    state.session_id = event_data["session_id"]

    if state.tracker is None:
        state.tracker = HistoryTracker(session_id=state.session_id, history=history)
        session_storage.save_session(session_id=state.session_id, first_message=state.first_message, agent_id=agent_id)

    if state.pending_user_message:
        state.tracker.save_user_message(state.pending_user_message)
        state.pending_user_message = None


@router.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
    agent_id: str | None = None,
    session_id: str | None = None,
    token: str | None = None
) -> None:
    """WebSocket endpoint for persistent multi-turn conversations.

    Protocol:
        Client sends: {"content": "user message"}
                      {"type": "user_answer", "question_id": "...", "answers": {...}}
        Server sends: {"type": "session_id", "session_id": "..."}
                      {"type": "text_delta", "text": "..."}
                      {"type": "tool_use/tool_result", ...}
                      {"type": "ask_user_question", "question_id": "...", "questions": [...]}
                      {"type": "done", "turn_count": N}
                      {"type": "error", "error": "..."}

    Query Parameters:
        agent_id: Optional agent ID to use.
        session_id: Optional session ID to resume.
        token: JWT access token (required).
    """
    # Validate JWT authentication and get username
    user_id, jti, username = await _validate_websocket_auth(websocket, token)

    await websocket.accept()
    logger.info(f"WebSocket connected, agent_id={agent_id}, session_id={session_id}, user={username}")

    # Use user-specific storage
    session_storage = get_user_session_storage(username)
    history = get_user_history_storage(username)

    try:
        existing_session, resume_session_id = await _resolve_session(websocket, session_id, session_storage)
    except SessionResolutionError:
        return

    question_manager = get_question_manager()

    state = WebSocketState(
        session_id=resume_session_id,
        turn_count=existing_session.turn_count if existing_session else 0,
        first_message=existing_session.first_message if existing_session else None,
        tracker=HistoryTracker(session_id=resume_session_id, history=history) if resume_session_id else None
    )

    question_handler = AskUserQuestionHandler(websocket, question_manager, state)

    options = create_agent_sdk_options(
        agent_id=agent_id,
        resume_session_id=resume_session_id,
        can_use_tool=question_handler.handle
    )
    client = ClaudeSDKClient(options)

    try:
        await _connect_sdk_client(websocket, client)
    except SDKConnectionError:
        return

    try:
        await websocket.send_json(_build_ready_message(resume_session_id, state.turn_count))
        await _run_message_loop(websocket, client, state, session_storage, history, question_manager, agent_id=agent_id)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected, session={state.session_id}, turns={state.turn_count}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        try:
            await client.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting SDK client: {e}")


async def _run_message_loop(
    websocket: WebSocket,
    client: ClaudeSDKClient,
    state: WebSocketState,
    session_storage: Any,
    history: Any,
    question_manager: QuestionManager,
    agent_id: str | None = None
) -> None:
    """Run the main message processing loop."""
    message_queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
    receiver_task = asyncio.create_task(
        _create_message_receiver(websocket, message_queue, question_manager, state)
    )

    try:
        while True:
            data = await message_queue.get()
            if data is None:
                break

            content = data.get("content", "")
            if not content:
                await websocket.send_json({"type": EventType.ERROR, "error": "Empty content"})
                continue

            if state.first_message is None:
                state.first_message = content[:FIRST_MESSAGE_TRUNCATE_LENGTH]

            if state.tracker:
                state.tracker.save_user_message(content)
            else:
                state.pending_user_message = content

            await _process_user_message(websocket, client, content, state, session_storage, history, agent_id=agent_id)
    finally:
        receiver_task.cancel()
        try:
            await receiver_task
        except asyncio.CancelledError:
            pass


async def _process_user_message(
    websocket: WebSocket,
    client: ClaudeSDKClient,
    content: str,
    state: WebSocketState,
    session_storage: Any,
    history: Any,
    agent_id: str | None = None
) -> None:
    """Process a single user message and stream the response."""
    try:
        await client.query(content)
        await _process_response_stream(client, websocket, state, session_storage, history, agent_id=agent_id)

        state.turn_count += 1

        if state.tracker:
            state.tracker.finalize_assistant_response()

        if state.session_id:
            session_storage.update_session(session_id=state.session_id, turn_count=state.turn_count)

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)

        if state.tracker and state.tracker.has_accumulated_text():
            state.tracker.finalize_assistant_response(metadata={"error": str(e)})

        await websocket.send_json({"type": EventType.ERROR, "error": str(e)})
