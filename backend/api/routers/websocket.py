"""WebSocket endpoint for persistent multi-turn conversations.

This approach keeps the SDK client in a single async context for the entire
WebSocket connection lifetime, avoiding the cancel scope task mismatch issue.

Supports AskUserQuestion tool callbacks for interactive user input during
agent execution.
Requires JWT token authentication via post-connect message (NOT query string).
"""
import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from claude_agent_sdk import ClaudeSDKClient
from api.utils.websocket import close_with_error
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
    ErrorCode,
    EventType,
    WSCloseCode,
)
from api.middleware.jwt_auth import validate_websocket_token
from api.services.history_tracker import HistoryTracker
from api.services.message_utils import message_to_dicts
from api.services.question_manager import QuestionManager, get_question_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

# Authentication timeout in seconds
AUTH_TIMEOUT = 5


@dataclass
class WebSocketState:
    """Mutable state for a WebSocket chat session."""

    session_id: str | None = None
    turn_count: int = 0
    first_message: str | None = None
    tracker: HistoryTracker | None = None
    pending_user_message: str | None = None
    last_ask_user_question_tool_use_id: str | None = None
    authenticated: bool = False  # Track authentication status


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


async def _validate_auth_token(token: str | None) -> tuple[str, str, str] | None:
    """Validate JWT authentication token.

    Returns:
        Tuple of (user_id, jti, username) if authenticated, None if not.

    Args:
        token: JWT token from auth message
    """
    if not token:
        return None

    try:
        user_id, jti = await validate_websocket_token(None, token)

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
            return None

        return user_id, jti, username
    except Exception as e:
        logger.error(f"Token validation failed: {e}")
        return None


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

    await websocket.send_json({
        "type": EventType.ERROR,
        "error": f"Session '{session_id}' not found",
        "code": ErrorCode.SESSION_NOT_FOUND
    })
    await close_with_error(websocket, WSCloseCode.SESSION_NOT_FOUND, "Session not found", raise_disconnect=False)
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
        await websocket.send_json({
            "type": EventType.ERROR,
            "error": f"Failed to initialize agent: {str(e)}",
            "code": ErrorCode.UNKNOWN
        })
        await close_with_error(websocket, WSCloseCode.SDK_CONNECTION_FAILED, "SDK client connection failed", raise_disconnect=False)
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

    Buffers messages until authentication is complete.
    """
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            # Handle authentication message
            if msg_type == EventType.AUTH:
                await message_queue.put(data)
                continue

            # Buffer other messages until authenticated
            if not state.authenticated:
                logger.info(f"Buffering message type '{msg_type}' until authentication completes")
                await message_queue.put(data)
                continue

            if msg_type == EventType.USER_ANSWER:
                question_id = data.get("question_id")
                if question_id:
                    logger.info(f"Received user_answer for question_id={question_id}")
                    # Save to history before submitting
                    if state.tracker:
                        state.tracker.process_event(EventType.USER_ANSWER, data)
                    await question_manager.submit_answer(question_id, data.get("answers", {}))
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
    session_id: str | None = None
) -> None:
    """WebSocket endpoint for persistent multi-turn conversations.

    Protocol:
        1. Client connects (no token in query string)
        2. Client sends: {"type": "auth", "token": "..."}
        3. Server validates and sends: {"type": "authenticated"}
        4. Server sends: {"type": "ready", ...}
        5. Client sends: {"content": "user message"}
                      {"type": "user_answer", "question_id": "...", "answers": {...}}
        Server sends: {"type": "session_id", "session_id": "..."}
                      {"type": "text_delta", "text": "..."}
                      {"type": "tool_use/tool_result", ...}
                      {"type": "ask_user_question", "question_id": "...", "questions": [...]}
                      {"type": "done", "turn_count": N}
                      {"type": "error", "error": "...", "code": "..."}

    Query Parameters:
        agent_id: Optional agent ID to use.
        session_id: Optional session ID to resume.
        token: NOT USED - token must be sent via auth message after connection.

    Security:
        - Token MUST be sent via auth message after connection
        - Connection closes if auth not received within 5 seconds
        - Messages are buffered until authentication completes
    """
    # Accept connection without authentication
    await websocket.accept()
    logger.info(f"WebSocket connection accepted, waiting for authentication, agent_id={agent_id}, session_id={session_id}")

    # Create message queue and start receiver task
    message_queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

    # Create initial state (not authenticated yet)
    state = WebSocketState(authenticated=False)

    # Wait for authentication message
    auth_result = await _wait_for_authentication(websocket, message_queue, state)
    if not auth_result:
        # Connection closed during auth
        return

    user_id, jti, username = auth_result
    logger.info(f"WebSocket authenticated for user={username}")

    state.authenticated = True

    # Send authenticated confirmation
    try:
        await websocket.send_json({"type": EventType.AUTHENTICATED})
    except Exception:
        logger.error("Failed to send authenticated confirmation")
        return

    # Use user-specific storage
    session_storage = get_user_session_storage(username)
    history = get_user_history_storage(username)

    try:
        existing_session, resume_session_id = await _resolve_session(websocket, session_id, session_storage)
    except SessionResolutionError:
        return

    # Update state with session info
    state.session_id = resume_session_id
    state.turn_count = existing_session.turn_count if existing_session else 0
    state.first_message = existing_session.first_message if existing_session else None
    state.tracker = HistoryTracker(session_id=resume_session_id, history=history) if resume_session_id else None

    question_manager = get_question_manager()
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
        # Send ready event after successful auth and SDK connection
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


async def _wait_for_authentication(
    websocket: WebSocket,
    message_queue: asyncio.Queue,
    state: WebSocketState
) -> tuple[str, str, str] | None:
    """Wait for authentication message from client.

    Returns:
        Tuple of (user_id, jti, username) if authenticated, None if failed.

    Buffers non-auth messages until authentication completes.
    """
    try:
        # Start message receiver in background
        receiver_task = asyncio.create_task(
            _create_message_receiver(websocket, message_queue, get_question_manager(), state)
        )

        # Wait for auth message with timeout
        auth_task = asyncio.create_task(_get_auth_message(message_queue))

        # Use timeout for authentication
        done, pending = await asyncio.wait(
            {auth_task, receiver_task},
            timeout=AUTH_TIMEOUT,
            return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Check if auth completed successfully
        if auth_task in done:
            auth_result = auth_task.result()
            if not auth_result:
                # Auth failed, send error and close
                try:
                    await websocket.send_json({
                        "type": EventType.ERROR,
                        "error": "Authentication failed",
                        "code": ErrorCode.TOKEN_INVALID
                    })
                except Exception:
                    pass
                await close_with_error(websocket, WSCloseCode.TOKEN_INVALID, "Authentication failed", raise_disconnect=False)
            return auth_result
        else:
            # Timeout - no auth message received
            logger.warning("Authentication timeout")
            try:
                await websocket.send_json({
                    "type": EventType.ERROR,
                    "error": "Authentication timeout",
                    "code": ErrorCode.TOKEN_INVALID
                })
            except Exception:
                pass
            await close_with_error(websocket, WSCloseCode.TOKEN_INVALID, "Authentication timeout", raise_disconnect=False)
            return None

    except Exception as e:
        logger.error(f"Error during authentication wait: {e}")
        return None


async def _get_auth_message(message_queue: asyncio.Queue) -> tuple[str, str, str] | None:
    """Extract and validate auth message from queue.

    Returns auth tuple or None if validation fails.
    Buffers non-auth messages for later processing.
    """
    buffered_messages = []

    try:
        while True:
            data = await message_queue.get()
            if data is None:
                # Connection closed
                return None

            msg_type = data.get("type")

            if msg_type == EventType.AUTH:
                token = data.get("token")
                auth_result = await _validate_auth_token(token)
                if auth_result:
                    # Put buffered messages back into queue
                    for msg in buffered_messages:
                        await message_queue.put(msg)
                    return auth_result
                else:
                    return None
            else:
                # Buffer non-auth messages
                buffered_messages.append(data)

    except Exception as e:
        logger.error(f"Error getting auth message: {e}")
        return None


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

    # Transfer any buffered messages to the new queue
    # Note: In the current implementation, messages are already being queued
    # by _create_message_receiver, so we don't need to transfer

    receiver_task = asyncio.create_task(
        _create_message_receiver(websocket, message_queue, question_manager, state)
    )

    try:
        while True:
            data = await message_queue.get()
            if data is None:
                break

            # Skip auth messages in the main loop (already handled)
            msg_type = data.get("type")
            if msg_type == EventType.AUTH:
                continue

            content = data.get("content", "")
            if not content:
                await websocket.send_json({
                    "type": EventType.ERROR,
                    "error": "Empty content",
                    "code": ErrorCode.UNKNOWN
                })
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

        await websocket.send_json({
            "type": EventType.ERROR,
            "error": str(e),
            "code": ErrorCode.UNKNOWN
        })
