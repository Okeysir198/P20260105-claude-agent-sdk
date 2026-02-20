"""Platform message processing worker.

Handles the full lifecycle of a platform message:
1. Resolve platform identity to internal username
2. Get or create a session
3. Invoke the Claude agent
4. Stream events incrementally back to the platform
"""

import asyncio
import logging
import mimetypes
import os
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk.types import (
    AssistantMessage,
    ResultMessage,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from agent.core.agent_options import create_agent_sdk_options
from agent.core.storage import get_user_history_storage, get_user_session_storage
from api.constants import FIRST_MESSAGE_TRUNCATE_LENGTH
from api.services.history_tracker import HistoryTracker
from api.services.session_setup import resolve_session_setup
from api.services.message_utils import message_to_dicts
from api.services.streaming_input import create_message_generator
from platforms.base import NormalizedMessage, NormalizedResponse, PlatformAdapter
from platforms.media import process_media_items
from platforms.event_formatter import (
    MESSAGE_SEND_DELAY,
    convert_tables_for_platform,
    format_file_download_message,
    format_new_session_requested,
    format_session_rotated,
    format_tool_result,
    format_tool_use,
)
from api.services.file_download_token import build_download_url, create_download_token
from api.utils.sensitive_data_filter import sanitize_paths, redact_sensitive_data
from platforms.identity import platform_identity_to_username
from platforms.session_bridge import clear_session_mapping, get_session_id_for_chat, is_session_expired, save_session_mapping

logger = logging.getLogger(__name__)


def _get_default_agent_id() -> str | None:
    """Get default agent ID from settings service with env var fallback."""
    try:
        from api.services.settings_service import get_settings_service
        return get_settings_service().get("default_agent_id")
    except Exception:
        return os.getenv("PLATFORM_DEFAULT_AGENT_ID")

# Keywords that trigger a new session (case-insensitive, checked as whole message or prefix)
_NEW_SESSION_KEYWORDS = {"new session", "new chat", "reset", "start over"}


def _resolve_written_file(
    tool_name: str, tool_input: dict, session_cwd: str
) -> tuple[str, str, str] | None:
    """Check if a tool_use is a Write tool and resolve the file path.

    Returns (abs_path, filename, mime_type) if valid, None otherwise.
    Only returns files within session_cwd (security boundary).
    """
    if tool_name != "Write":
        return None

    file_path = tool_input.get("file_path", "")
    if not file_path:
        return None

    # Resolve relative paths against session_cwd
    p = Path(file_path)
    if not p.is_absolute():
        p = Path(session_cwd) / p
    abs_path = str(p.resolve())

    # Security: only allow files within session_cwd
    cwd_resolved = str(Path(session_cwd).resolve())
    if not abs_path.startswith(cwd_resolved + "/") and abs_path != cwd_resolved:
        return None

    filename = p.name
    mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return abs_path, filename, mime_type


def _is_new_session_request(text: str) -> bool:
    """Check if the message text is a request to start a new session."""
    normalized = text.strip().lower()
    return normalized in _NEW_SESSION_KEYWORDS


# Files below this size are sent directly to the platform; larger ones get a download link
DIRECT_SEND_MAX_BYTES = 10 * 1024 * 1024  # 10MB


async def _deliver_file_to_platform(
    adapter: PlatformAdapter,
    chat_id: str,
    abs_path: str,
    filename: str,
    mime_type: str,
    username: str,
    cwd_id: str,
    session_cwd: str,
    send_msg_fn,
) -> None:
    """Deliver an agent-created file to the platform.

    Strategy: send directly if < 10MB, otherwise generate a download link.
    If direct send fails, fall back to download link.
    """
    path = Path(abs_path)
    if not path.exists():
        return

    size_bytes = path.stat().st_size

    # Compute relative path from session_cwd for the download token
    try:
        rel_path = str(path.resolve().relative_to(Path(session_cwd).resolve()))
    except ValueError:
        # File outside session_cwd — cannot generate token
        return

    sent_directly = False
    if size_bytes < DIRECT_SEND_MAX_BYTES:
        sent_directly = await adapter.send_file(chat_id, abs_path, filename, mime_type)

    if not sent_directly:
        token = create_download_token(username, cwd_id, rel_path)
        url = build_download_url(token)
        await send_msg_fn(format_file_download_message(filename, size_bytes, url))


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
    effective_agent_id = agent_id or _get_default_agent_id()

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

        # Check for "new session" keyword — user wants to start fresh
        force_new_session = _is_new_session_request(msg.text)
        if force_new_session:
            clear_session_mapping(username, msg.platform_chat_id)
            logger.info(
                f"User requested new session via keyword: "
                f"chat={msg.platform_chat_id}"
            )
            # Send confirmation and return — don't forward the keyword to the agent
            await adapter.send_response(
                msg.platform_chat_id,
                NormalizedResponse(text=format_new_session_requested()),
            )
            return

        # Get storage
        session_storage = get_user_session_storage(username)
        history_storage = get_user_history_storage(username)

        # Look up or create session
        session_id = get_session_id_for_chat(username, msg.platform_chat_id)
        resume_session_id = session_id

        expired_session = False
        if session_id:
            existing = session_storage.get_session(session_id)
            if existing and is_session_expired(existing):
                logger.info(
                    f"Platform session {session_id} expired for chat "
                    f"{msg.platform_chat_id} — starting fresh"
                )
                existing = None
                session_id = None
                resume_session_id = None
                turn_count = 0
                expired_session = True
            elif existing:
                turn_count = existing.turn_count
            else:
                # Session mapping exists but session was deleted — start fresh
                existing = None
                session_id = None
                resume_session_id = None
                turn_count = 0
        else:
            existing = None
            turn_count = 0

        setup = resolve_session_setup(username, existing, resume_session_id)
        cwd_id = setup.cwd_id

        # --- Process media attachments ---
        sdk_content: str | list[dict[str, Any]] = msg.text
        if msg.media:
            try:
                download_kwargs = adapter.get_media_download_kwargs()

                processed = await process_media_items(
                    media_list=msg.media,
                    platform=msg.platform.value,
                    file_storage=setup.file_storage,
                    **download_kwargs,
                )

                # Build multi-part content if we have image blocks
                if processed.content_blocks or processed.file_annotations:
                    parts: list[dict[str, Any]] = []
                    # Combine text + file annotations
                    combined_text = msg.text or ""
                    if processed.file_annotations:
                        annotation_text = "\n".join(processed.file_annotations)
                        combined_text = f"{combined_text}\n{annotation_text}" if combined_text else annotation_text
                    if combined_text:
                        parts.append({"type": "text", "text": combined_text})
                    # Add image content blocks
                    parts.extend(processed.content_blocks)
                    sdk_content = parts

                if processed.errors:
                    for err in processed.errors:
                        logger.warning(f"Media processing error: {err}")

            except Exception as e:
                logger.error(f"Media processing failed: {e}", exc_info=True)
                # Fall through — send text-only message

        options = create_agent_sdk_options(
            agent_id=effective_agent_id,
            resume_session_id=resume_session_id,
            session_cwd=setup.session_cwd,
            permission_folders=setup.permission_folders,
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
                tracker.save_user_message(sdk_content)  # type: ignore[arg-type]

            # Build first_message preview
            first_message = msg.text[:FIRST_MESSAGE_TRUNCATE_LENGTH] if msg.text else None

            # Send user message to agent
            message_gen = create_message_generator(
                sdk_content, session_id or "default"
            )
            await client.query(message_gen, session_id=session_id or "default")

            # --- Incremental event delivery ---
            # Instead of accumulating all text into one message, we send
            # each meaningful event (text chunks, tool_use, tool_result)
            # as a separate platform message so users can follow along.

            accumulated_text = ""
            new_session_id: str | None = session_id
            has_sent_any = False
            tool_name_map: dict[str, str] = {}  # tool_use_id → tool_name
            tool_input_map: dict[str, dict] = {}  # tool_use_id → tool_input

            async def _send_msg(text: str) -> None:
                """Send one message to the platform with rate-limit delay."""
                nonlocal has_sent_any
                try:
                    # Sanitize: first remove absolute paths, then redact sensitive data
                    sanitized = sanitize_paths(text)
                    sanitized = redact_sensitive_data(sanitized)

                    # Debug: Log if sanitization changed anything
                    if text != sanitized:
                        logger.warning(f"Sanitization redacted sensitive data in message to {msg.platform_chat_id}")
                        logger.debug(f"Original length: {len(text)}, Sanitized length: {len(sanitized)}")

                    await adapter.send_response(
                        msg.platform_chat_id, NormalizedResponse(text=sanitized)
                    )
                    has_sent_any = True
                    await asyncio.sleep(MESSAGE_SEND_DELAY)
                    # Refresh typing indicator for next chunk
                    try:
                        await adapter.send_typing_indicator(msg.platform_chat_id)
                    except Exception:
                        pass
                except Exception as e:
                    logger.warning(f"Failed to send platform message: {e}")

            async def _flush_text() -> None:
                """Send accumulated text as a message, then reset buffer."""
                nonlocal accumulated_text
                text = accumulated_text.strip()
                if text:
                    text = convert_tables_for_platform(text)
                    await _send_msg(text)
                    accumulated_text = ""

            if expired_session:
                await _send_msg(format_session_rotated())

            async for sdk_msg in client.receive_response():
                if isinstance(sdk_msg, AssistantMessage):
                    if tracker:
                        tracker.save_from_assistant_message(sdk_msg)
                    # Extract tool_use blocks and send as intermediate messages
                    for block in getattr(sdk_msg, "content", []):
                        if isinstance(block, ToolUseBlock):
                            await _flush_text()
                            tool_name_map[block.id] = block.name
                            tool_input_map[block.id] = block.input if isinstance(block.input, dict) else {}
                            await _send_msg(
                                format_tool_use(block.name, block.input)
                            )

                elif isinstance(sdk_msg, UserMessage):
                    if tracker:
                        tracker.save_from_user_message(sdk_msg)
                    # Extract tool_result blocks and send status lines
                    for block in getattr(sdk_msg, "content", []):
                        if isinstance(block, ToolResultBlock):
                            tool_name = tool_name_map.get(
                                block.tool_use_id, "Tool"
                            )
                            content = block.content if isinstance(block.content, str) else str(block.content or "")
                            is_error = block.is_error or False
                            await _send_msg(
                                format_tool_result(tool_name, content, is_error)
                            )
                            # Send file if Write tool succeeded
                            if not is_error:
                                file_info = _resolve_written_file(
                                    tool_name,
                                    tool_input_map.get(block.tool_use_id, {}),
                                    setup.session_cwd,
                                )
                                if file_info:
                                    await _deliver_file_to_platform(
                                        adapter, msg.platform_chat_id,
                                        file_info[0], file_info[1], file_info[2],
                                        username, cwd_id, setup.session_cwd, _send_msg,
                                    )

                elif isinstance(sdk_msg, ResultMessage):
                    result_session_id = getattr(sdk_msg, "session_id", None)
                    if result_session_id and not new_session_id:
                        new_session_id = result_session_id
                    break

                else:
                    # Handle StreamEvent-like messages
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
                                session_storage.save_session(
                                    session_id=new_session_id,
                                    first_message=first_message,
                                    user_id=username,
                                    agent_id=effective_agent_id,
                                    cwd_id=cwd_id,
                                    permission_folders=setup.permission_folders,
                                    client_type=msg.platform.value,
                                )
                                tracker.save_user_message(sdk_content)  # type: ignore[arg-type]
                                save_session_mapping(
                                    username, msg.platform_chat_id, new_session_id
                                )

                        elif event_type == "text_delta":
                            # Accumulate text (will flush before tool events)
                            accumulated_text += event_data.get("text", "")
                            if tracker:
                                tracker.process_event(event_type, event_data)

                        elif event_type == "tool_use":
                            # Flush pending text before tool status
                            await _flush_text()
                            tool_id = event_data.get("id", "")
                            tool_name = event_data.get("name", "unknown")
                            tool_input = event_data.get("input")
                            tool_name_map[tool_id] = tool_name
                            tool_input_map[tool_id] = tool_input if isinstance(tool_input, dict) else {}
                            await _send_msg(format_tool_use(tool_name, tool_input))
                            if tracker:
                                tracker.process_event(event_type, event_data)

                        elif event_type == "tool_result":
                            tool_use_id = event_data.get("tool_use_id", "")
                            tool_name = tool_name_map.get(tool_use_id, "Tool")
                            content = event_data.get("content", "")
                            is_error = event_data.get("is_error", False)
                            await _send_msg(
                                format_tool_result(tool_name, content, is_error)
                            )
                            if tracker:
                                tracker.process_event(event_type, event_data)
                            # Send file if Write tool succeeded
                            if not is_error:
                                file_info = _resolve_written_file(
                                    tool_name,
                                    tool_input_map.get(tool_use_id, {}),
                                    setup.session_cwd,
                                )
                                if file_info:
                                    await _deliver_file_to_platform(
                                        adapter, msg.platform_chat_id,
                                        file_info[0], file_info[1], file_info[2],
                                        username, cwd_id, setup.session_cwd, _send_msg,
                                    )

                        elif event_type and tracker:
                            tracker.process_event(event_type, event_data)

            # Flush any remaining accumulated text
            await _flush_text()

            # Finalize tracker
            if tracker:
                tracker.finalize_assistant_response()

            # Update turn count
            turn_count += 1
            if new_session_id:
                session_storage.update_session(
                    session_id=new_session_id, turn_count=turn_count
                )
                if not session_id and new_session_id:
                    save_session_mapping(
                        username, msg.platform_chat_id, new_session_id
                    )

            # Fallback if nothing was sent at all
            if not has_sent_any:
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
