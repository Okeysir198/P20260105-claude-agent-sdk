"""WebSocket endpoint for persistent multi-turn conversations.

This approach keeps the SDK client in a single async context for the entire
WebSocket connection lifetime, avoiding the cancel scope task mismatch issue.

Supports AskUserQuestion tool callbacks for interactive user input during
agent execution.
Requires JWT token authentication.
"""
import asyncio
import json as json_module
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk.types import (
    AssistantMessage,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    TextBlock,
    ToolPermissionContext,
    UserMessage,
)

from agent.core.agent_options import create_agent_sdk_options
from agent.core.file_storage import FileStorage
from agent.core.storage import get_data_dir, get_user_history_storage, get_user_session_storage
from api.constants import (
    ASK_USER_QUESTION_TIMEOUT,
    FIRST_MESSAGE_TRUNCATE_LENGTH,
    TOOL_REF_PATTERN,
    EventType,
    WSCloseCode,
)
from api.middleware.jwt_auth import validate_websocket_token, WebSocketAuthError
from api.services.content_normalizer import extract_text_content, normalize_content
from api.services.history_tracker import HistoryTracker
from api.services.message_utils import message_to_dicts
from api.services.question_manager import QuestionManager, get_question_manager
from api.services.streaming_input import create_message_generator
from api.utils.websocket import close_with_error

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@dataclass
class WebSocketState:
    """Mutable state for a WebSocket chat session."""

    session_id: str | None = None
    turn_count: int = 0
    first_message: str | None = None
    tracker: HistoryTracker | None = None
    pending_user_message: str | list | None = None  # Can be string or multi-part content
    last_ask_user_question_tool_use_id: str | None = None
    is_processing: bool = False
    cancel_requested: bool = False
    pending_tool_use_ids: list[str] = field(default_factory=list)
    # Stream-level AskUserQuestion handling (fallback when PreToolUse hook doesn't fire)
    ask_user_question_sent_from_stream: bool = False
    ask_user_question_handled_by_callback: bool = False
    # File storage (always created eagerly with pre-generated cwd_id)
    file_storage: FileStorage | None = None
    username: str | None = None
    cwd_id: str | None = None  # Pre-generated file storage directory ID


def _normalize_questions_field(questions: Any, context: str = "") -> list:
    """Normalize the questions field from AskUserQuestion tool input.

    The model/provider sometimes sends questions as a JSON string instead of
    a proper array. This function handles both formats and returns a list.

    Args:
        questions: The questions field value - may be a list (correct) or
            a JSON string (needs parsing).
        context: Description of where this normalization is being called from,
            used for logging.

    Returns:
        A list of question dicts. Returns empty list if parsing fails.
    """
    if isinstance(questions, list):
        return questions

    if isinstance(questions, str):
        stripped = questions.strip()
        if not stripped:
            logger.warning(f"[{context}] AskUserQuestion questions is empty string, returning empty list")
            return []

        try:
            parsed = json_module.loads(stripped)
            if isinstance(parsed, list):
                logger.info(
                    f"[{context}] Parsed AskUserQuestion questions from JSON string: "
                    f"{len(parsed)} questions"
                )
                return parsed
            else:
                logger.warning(
                    f"[{context}] Parsed AskUserQuestion questions JSON is not a list "
                    f"(got {type(parsed).__name__}), returning empty list"
                )
                return []
        except (json_module.JSONDecodeError, TypeError) as e:
            logger.error(
                f"[{context}] Failed to parse AskUserQuestion questions string as JSON: {e}. "
                f"Raw value (first 200 chars): {stripped[:200]}"
            )
            return []

    logger.warning(
        f"[{context}] AskUserQuestion questions has unexpected type {type(questions).__name__}, "
        f"returning empty list"
    )
    return []


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

        Handles the case where the `questions` field may be a JSON string
        instead of an array (due to model/provider serialization issues).
        """
        logger.info(f"can_use_tool callback invoked: tool_name={tool_name}")

        if tool_name != "AskUserQuestion":
            return PermissionResultAllow(updated_input=tool_input)

        # Mark that the callback was invoked (so stream-level fallback is skipped)
        self._state.ask_user_question_handled_by_callback = True

        # Use the tool_use_id from the streamed event (stored in state), or generate a new UUID as fallback
        question_id = self._state.last_ask_user_question_tool_use_id or str(uuid.uuid4())
        questions = tool_input.get("questions", [])

        # Normalize questions: parse JSON string to array if needed
        questions = _normalize_questions_field(questions, context="can_use_tool")
        logger.info(f"AskUserQuestion invoked: question_id={question_id}, questions={len(questions)}")

        # If the question was already sent from the stream, skip sending again
        if self._state.ask_user_question_sent_from_stream:
            logger.info(f"AskUserQuestion already sent from stream, skipping duplicate send: question_id={question_id}")
        elif not await self._send_question(question_id, questions):
            return PermissionResultDeny(message="Failed to send question to client")

        return await self._wait_for_answer(question_id, questions)

    async def _send_question(self, question_id: str, questions: list) -> bool:
        """Send question event to client. Returns True on success."""
        try:
            logger.info(f"Sending ask_user_question event via WebSocket: question_id={question_id}, num_questions={len(questions)}")
            await self._websocket.send_json({
                "type": EventType.ASK_USER_QUESTION,
                "question_id": question_id,
                "questions": questions,
                "timeout": self._timeout
            })
            logger.info(f"ask_user_question event sent successfully: question_id={question_id}")
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
        Tuple of (user_id, jti, username) if authenticated.

    Raises:
        WebSocketAuthError: If authentication fails
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
        await close_with_error(websocket, WSCloseCode.AUTH_FAILED, "Token missing username", raise_disconnect=False)
        raise WebSocketAuthError("Token missing username")

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
        await websocket.send_json({"type": EventType.ERROR, "error": f"Failed to initialize agent: {str(e)}"})
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

            if msg_type == EventType.CANCEL_REQUEST:
                logger.info("Cancel request received")
                state.cancel_requested = True
                question_manager.cancel_question(state.last_ask_user_question_tool_use_id or "")
                await message_queue.put({"type": EventType.CANCEL_REQUEST})
                continue

            if msg_type == EventType.COMPACT_REQUEST:
                logger.info("Compact request received")
                await message_queue.put({"type": EventType.COMPACT_REQUEST})
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
    agent_id: str | None = None,
    question_manager: QuestionManager | None = None,
) -> None:
    """Process the response stream from the SDK client."""
    # Reset stream-level AskUserQuestion state for this turn
    state.ask_user_question_sent_from_stream = False
    state.ask_user_question_handled_by_callback = False

    async for msg in client.receive_response():
        # Log raw SDK message type and content for debugging
        msg_type_name = type(msg).__name__
        logger.info(f"[SDK RAW] Message type: {msg_type_name}")
        if hasattr(msg, 'content'):
            try:
                if isinstance(msg.content, list):
                    for i, block in enumerate(msg.content):
                        block_type = type(block).__name__
                        block_data = block.__dict__ if hasattr(block, '__dict__') else str(block)
                        logger.info(f"[SDK RAW]   Block[{i}]: type={block_type}, data={json_module.dumps(block_data, default=str)[:500]}")
                else:
                    logger.info(f"[SDK RAW]   Content: {str(msg.content)[:500]}")
            except Exception as e:
                logger.info(f"[SDK RAW]   Content logging error: {e}")

        # Check for cancel request
        if state.cancel_requested:
            logger.info("Cancel requested, interrupting SDK client")
            await client.interrupt()
            state.cancel_requested = False

            await _send_cancelled_tool_results(websocket, state)

            # Save cancelled event to history
            if state.tracker:
                state.tracker.process_event(EventType.CANCELLED, {"cancelled": True})
            await websocket.send_json({"type": EventType.CANCELLED})
            break

        # Use message_to_dicts to get all events (handles UserMessage with multiple tool_results)
        events = message_to_dicts(msg)

        for event_data in events:
            event_type = event_data.get("type")

            # Log converted events for AskUserQuestion debugging
            if event_type in (EventType.TOOL_USE, EventType.TOOL_RESULT):
                logger.info(f"[SDK EVENT] {event_type}: {json_module.dumps(event_data, default=str)[:500]}")

            # Track tool_use_ids for pending tool uses
            if event_type == EventType.TOOL_USE:
                tool_use_id = event_data.get("id")
                if tool_use_id:
                    state.pending_tool_use_ids.append(tool_use_id)
                # Capture tool_use_id for AskUserQuestion to use as question_id
                if event_data.get("name") == "AskUserQuestion":
                    logger.info(f"AskUserQuestion tool_use detected in response stream: tool_use_id={tool_use_id}")
                    state.last_ask_user_question_tool_use_id = tool_use_id

                    # Normalize the questions field in the tool_use event before
                    # sending to the frontend. The model/provider sometimes sends
                    # questions as a JSON string instead of an array.
                    tool_input = event_data.get("input", {})
                    if tool_input and isinstance(tool_input, dict):
                        raw_questions = tool_input.get("questions")
                        if raw_questions is not None:
                            normalized = _normalize_questions_field(raw_questions, context="stream_tool_use")
                            if normalized != raw_questions:
                                tool_input["questions"] = normalized
                                event_data["input"] = tool_input
                                logger.info(
                                    f"Normalized AskUserQuestion questions in stream event: "
                                    f"tool_use_id={tool_use_id}, num_questions={len(normalized)}"
                                )

                    # Stream-level fallback: Send ask_user_question event directly
                    # to frontend. This handles the case where the CLI validates
                    # AskUserQuestion input and rejects string-encoded questions
                    # BEFORE the PreToolUse hook or can_use_tool callback fires.
                    normalized_questions = tool_input.get("questions", [])
                    if isinstance(normalized_questions, str):
                        normalized_questions = _normalize_questions_field(normalized_questions, context="stream_fallback")
                    if normalized_questions and question_manager is not None:
                        question_id = tool_use_id or str(uuid.uuid4())
                        try:
                            logger.info(
                                f"[Stream Fallback] Sending ask_user_question event directly: "
                                f"question_id={question_id}, num_questions={len(normalized_questions)}"
                            )
                            await websocket.send_json({
                                "type": EventType.ASK_USER_QUESTION,
                                "question_id": question_id,
                                "questions": normalized_questions,
                                "timeout": ASK_USER_QUESTION_TIMEOUT,
                            })
                            question_manager.create_question(question_id, normalized_questions)
                            state.ask_user_question_sent_from_stream = True
                            logger.info(
                                f"[Stream Fallback] ask_user_question event sent and question created: "
                                f"question_id={question_id}"
                            )
                        except Exception as e:
                            logger.error(f"[Stream Fallback] Failed to send ask_user_question: {e}")

            # Remove tool_use_id from pending list when we get the result
            if event_type == EventType.TOOL_RESULT:
                tool_use_id = event_data.get("tool_use_id")
                if tool_use_id and tool_use_id in state.pending_tool_use_ids:
                    state.pending_tool_use_ids.remove(tool_use_id)

            # Determine if this message has typed SDK objects for direct history saving
            typed_history = isinstance(msg, (AssistantMessage, UserMessage))

            if event_type == EventType.SESSION_ID:
                _handle_session_id_event(event_data, state, session_storage, history, agent_id=agent_id)
            elif state.tracker and not typed_history:
                # Only use dict-based process_event for StreamEvent/ResultMessage/etc.
                # AssistantMessage and UserMessage use typed save_from_* methods below.
                # Flush-before-tool_use is handled inside process_event() itself.
                state.tracker.process_event(event_type, event_data)

            await websocket.send_json(event_data)

        # Typed history saving for AssistantMessage and UserMessage.
        # Uses block attributes directly instead of dict-based process_event.
        if isinstance(msg, AssistantMessage) and state.tracker:
            # Save all blocks (text, tool_use, tool_result) to history via typed path
            state.tracker.save_from_assistant_message(msg)

            # Send canonical text to frontend for live display cleanup.
            # Strip proxy-injected tool references from TextBlock text since
            # the SDK assembles TextBlock from the same text_delta stream.
            text_blocks = []
            for b in msg.content:
                if isinstance(b, TextBlock) and b.text.strip():
                    cleaned = TOOL_REF_PATTERN.sub('', b.text).strip()
                    if cleaned:
                        text_blocks.append(cleaned)
            if text_blocks:
                canonical_text = "\n\n".join(text_blocks)
                await websocket.send_json({
                    "type": EventType.ASSISTANT_TEXT,
                    "text": canonical_text,
                })

        elif isinstance(msg, UserMessage) and state.tracker:
            state.tracker.save_from_user_message(msg)

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
        session_storage.save_session(
            session_id=state.session_id,
            first_message=state.first_message,
            user_id=state.username,
            agent_id=agent_id,
            cwd_id=state.cwd_id,
        )

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

    # Always create an isolated session file directory
    # For resumed sessions: use the stored cwd_id
    # For new sessions: pre-generate a unique cwd_id (UUID)
    if resume_session_id and existing_session:
        cwd_id = existing_session.cwd_id or resume_session_id  # backward compat for old sessions
        permission_folders = existing_session.permission_folders or ["/tmp"]
    else:
        cwd_id = str(uuid.uuid4())
        permission_folders = ["/tmp"]

    file_storage = FileStorage(username=username, session_id=cwd_id)
    session_cwd = str(file_storage.get_session_dir())
    logger.info(f"FileStorage ready: cwd_id={cwd_id}, cwd={session_cwd}, new={not resume_session_id}, user={username}")

    question_manager = get_question_manager()

    state = WebSocketState(
        session_id=resume_session_id,
        turn_count=existing_session.turn_count if existing_session else 0,
        first_message=existing_session.first_message if existing_session else None,
        tracker=HistoryTracker(session_id=resume_session_id, history=history) if resume_session_id else None,
        file_storage=file_storage,
        username=username,
        cwd_id=cwd_id,
    )

    question_handler = AskUserQuestionHandler(websocket, question_manager, state)

    # Pass session dirs to SDK options: cwd = isolated session folder
    options = create_agent_sdk_options(
        agent_id=agent_id,
        resume_session_id=resume_session_id,
        can_use_tool=question_handler.handle,
        session_cwd=session_cwd,
        permission_folders=permission_folders,
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


async def _handle_compact_request(
    websocket: WebSocket,
    client: ClaudeSDKClient,
    state: WebSocketState
) -> None:
    """Handle context compact request by sending /compact to the SDK."""
    await websocket.send_json({"type": EventType.COMPACT_STARTED})

    try:
        # Use SDK's built-in /compact command
        await client.query("/compact")
        async for msg in client.receive_response():
            # Wait for completion, optionally log progress
            pass

        await websocket.send_json({
            "type": EventType.COMPACT_COMPLETED,
            "session_id": state.session_id
        })
        logger.info(f"Compact completed for session={state.session_id}")
    except Exception as e:
        logger.error(f"Compact failed: {e}")
        await websocket.send_json({
            "type": EventType.ERROR,
            "error": f"Compact failed: {str(e)}"
        })


async def _send_cancelled_tool_results(
    websocket: WebSocket,
    state: WebSocketState,
) -> None:
    """Send interrupted tool_result events for all pending tool uses.

    Args:
        websocket: WebSocket connection to send events to
        state: WebSocket state containing pending_tool_use_ids and tracker
    """
    for tool_use_id in state.pending_tool_use_ids:
        tool_result_event = {
            "type": EventType.TOOL_RESULT,
            "tool_use_id": tool_use_id,
            "content": "[Request interrupted by user]",
            "is_error": True
        }
        await websocket.send_json(tool_result_event)
        # Also save to history
        if state.tracker:
            state.tracker.process_event(EventType.TOOL_RESULT, tool_result_event)
    state.pending_tool_use_ids.clear()


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

            # Handle compact request
            if data.get("type") == EventType.COMPACT_REQUEST:
                await _handle_compact_request(websocket, client, state)
                continue

            # Handle cancel request
            if data.get("type") == EventType.CANCEL_REQUEST:
                # If not currently processing (stream finished or not started),
                # send cancelled immediately to reset frontend state
                if not state.is_processing:
                    logger.info("Cancel request received but not processing, sending cancelled")
                    state.cancel_requested = False
                    await _send_cancelled_tool_results(websocket, state)

                    # Save cancelled event to history
                    if state.tracker:
                        state.tracker.process_event(EventType.CANCELLED, {"cancelled": True})
                    await websocket.send_json({"type": EventType.CANCELLED})
                # If processing, _process_response_stream will handle it via state.cancel_requested flag
                continue

            content = data.get("content", "")
            if not content:
                await websocket.send_json({"type": EventType.ERROR, "error": "Empty content"})
                continue

            # Debug logging
            logger.info(f"Received content type: {type(content)}")
            if isinstance(content, list):
                logger.info(f"Content blocks: {len(content)} blocks")
                for i, block in enumerate(content):
                    logger.info(f"  Block {i}: type={block.get('type')}, has_source={'source' in block}")

            # Normalize and validate content (supports both string and multi-part)
            try:
                normalized_blocks = normalize_content(content)
                logger.info(f"Normalized {len(normalized_blocks)} blocks successfully")
            except (ValueError, TypeError) as e:
                await websocket.send_json({
                    "type": EventType.ERROR,
                    "error": f"Invalid content format: {e}"
                })
                continue

            # Extract text for first_message preview (legacy compatibility)
            text_content = extract_text_content(content)
            if state.first_message is None:
                state.first_message = text_content[:FIRST_MESSAGE_TRUNCATE_LENGTH]

            # Save user message to history (preserves full multi-part content including images)
            if state.tracker:
                state.tracker.save_user_message(content)
            else:
                # Store full content for pending message (not just text)
                state.pending_user_message = content

            # Track processing state for cancel handling
            state.is_processing = True
            try:
                await _process_user_message(websocket, client, content, state, session_storage, history, agent_id=agent_id, question_manager=question_manager)
            finally:
                state.is_processing = False
    finally:
        receiver_task.cancel()
        try:
            await receiver_task
        except asyncio.CancelledError:
            pass


async def _process_user_message(
    websocket: WebSocket,
    client: ClaudeSDKClient,
    content: str | list,
    state: WebSocketState,
    session_storage: Any,
    history: Any,
    agent_id: str | None = None,
    question_manager: QuestionManager | None = None,
) -> None:
    """Process a single user message and stream the response.

    Args:
        content: User message content as string (legacy) or list of content blocks (multi-part).
            Multi-part format supports text, images, and other content types.
        question_manager: Optional QuestionManager for stream-level AskUserQuestion fallback.
    """
    try:
        # Use streaming input mode for both simple and multi-part content
        # This provides consistent handling and future-proofs for dynamic message injection
        session_id = state.session_id or "default"
        message_generator = create_message_generator(content, session_id)

        await client.query(message_generator, session_id=session_id)
        await _process_response_stream(client, websocket, state, session_storage, history, agent_id=agent_id, question_manager=question_manager)

        state.turn_count += 1

        if state.tracker:
            state.tracker.finalize_assistant_response()

        if state.session_id:
            session_storage.update_session(session_id=state.session_id, turn_count=state.turn_count)

        # Stream-level AskUserQuestion fallback:
        # If we sent the question from the stream but can_use_tool was never called
        # (CLI validation rejected the tool), wait for the user's answer and
        # auto-inject it as a follow-up message so the agent can continue.
        if (
            state.ask_user_question_sent_from_stream
            and not state.ask_user_question_handled_by_callback
            and question_manager is not None
        ):
            question_id = state.last_ask_user_question_tool_use_id
            if question_id:
                logger.info(
                    f"[Stream Fallback] can_use_tool was NOT called for AskUserQuestion. "
                    f"Waiting for user answer to auto-inject: question_id={question_id}"
                )
                try:
                    answers = await question_manager.wait_for_answer(
                        question_id, timeout=ASK_USER_QUESTION_TIMEOUT
                    )
                    logger.info(f"[Stream Fallback] Received user answer: question_id={question_id}")

                    # Build answer text to inject as a follow-up user message
                    answer_parts = []
                    if isinstance(answers, dict):
                        for key, value in answers.items():
                            answer_parts.append(f"- {key}: {value}")
                    elif isinstance(answers, list):
                        for ans in answers:
                            if isinstance(ans, dict):
                                answer_parts.append(f"- {ans.get('answer', str(ans))}")
                            else:
                                answer_parts.append(f"- {ans}")
                    else:
                        answer_parts.append(str(answers))

                    answer_text = (
                        "The user answered the question:\n"
                        + "\n".join(answer_parts)
                    )

                    # Send done event for the previous turn
                    await websocket.send_json({
                        "type": EventType.DONE,
                        "turn_count": state.turn_count,
                    })

                    # Auto-inject the answer as a new user message
                    logger.info(f"[Stream Fallback] Auto-injecting user answer as new message")
                    if state.tracker:
                        state.tracker.save_user_message(answer_text)

                    state.is_processing = True
                    try:
                        message_generator = create_message_generator(answer_text, session_id)
                        await client.query(message_generator, session_id=session_id)
                        await _process_response_stream(
                            client, websocket, state, session_storage, history,
                            agent_id=agent_id, question_manager=question_manager
                        )
                        state.turn_count += 1
                        if state.tracker:
                            state.tracker.finalize_assistant_response()
                        if state.session_id:
                            session_storage.update_session(
                                session_id=state.session_id, turn_count=state.turn_count
                            )
                    finally:
                        state.is_processing = False

                except asyncio.TimeoutError:
                    logger.warning(f"[Stream Fallback] Timeout waiting for user answer: question_id={question_id}")
                except Exception as e:
                    logger.error(f"[Stream Fallback] Error in auto-inject flow: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)

        if state.tracker and state.tracker.has_accumulated_text():
            state.tracker.finalize_assistant_response(metadata={"error": str(e)})

        await websocket.send_json({"type": EventType.ERROR, "error": str(e)})
