"""Platform chat to session mapping.

Bridges platform chat IDs to internal session IDs so that multi-turn
conversations are maintained across webhook calls.
"""

import json
import logging
from pathlib import Path

from agent.core.storage import get_user_session_storage, get_user_history_storage, SessionStorage, HistoryStorage

logger = logging.getLogger(__name__)

PLATFORM_SESSIONS_FILENAME = "platform_sessions.json"


def _get_platform_sessions_file(username: str) -> Path:
    """Get the platform sessions mapping file for a user."""
    session_storage = get_user_session_storage(username)
    return session_storage._data_dir / PLATFORM_SESSIONS_FILENAME


def _read_mappings(filepath: Path) -> dict[str, str]:
    """Read chat_id → session_id mappings from file."""
    if not filepath.exists():
        return {}
    try:
        content = filepath.read_text().strip()
        if not content:
            return {}
        return json.loads(content)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error reading platform sessions file: {e}")
        return {}


def _write_mappings(filepath: Path, mappings: dict[str, str]) -> None:
    """Write chat_id → session_id mappings to file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(filepath, "w") as f:
            json.dump(mappings, f, indent=2)
    except IOError as e:
        logger.error(f"Error writing platform sessions file: {e}")


def get_session_id_for_chat(username: str, chat_id: str) -> str | None:
    """Look up the session ID mapped to a platform chat.

    Args:
        username: Internal username (from identity mapper).
        chat_id: Platform chat identifier.

    Returns:
        Session ID if a mapping exists, None otherwise.
    """
    filepath = _get_platform_sessions_file(username)
    mappings = _read_mappings(filepath)
    return mappings.get(chat_id)


def save_session_mapping(username: str, chat_id: str, session_id: str) -> None:
    """Persist a chat_id → session_id mapping.

    Args:
        username: Internal username.
        chat_id: Platform chat identifier.
        session_id: Internal session identifier.
    """
    filepath = _get_platform_sessions_file(username)
    mappings = _read_mappings(filepath)
    mappings[chat_id] = session_id
    _write_mappings(filepath, mappings)
    logger.info(f"Saved platform session mapping: {chat_id} -> {session_id} for {username}")


def get_storage(username: str) -> tuple[SessionStorage, HistoryStorage]:
    """Get session and history storage for a platform user.

    Convenience wrapper that returns both storage instances needed
    for agent message processing.

    Args:
        username: Internal username.

    Returns:
        Tuple of (SessionStorage, HistoryStorage).
    """
    return get_user_session_storage(username), get_user_history_storage(username)
