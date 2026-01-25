"""Unified session storage for Claude Agent SDK.

Provides a single storage system for both CLI and API modes.
Sessions are stored in {DATA_DIR}/sessions.json with rich metadata.
Message history is stored in {DATA_DIR}/history/{session_id}.jsonl.

Configure data directory via DATA_DIR environment variable.
"""
import json
import logging
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from agent import PROJECT_ROOT

logger = logging.getLogger(__name__)

# Configuration constants
MAX_SESSIONS = 20
SESSIONS_FILENAME = "sessions.json"
HISTORY_DIRNAME = "history"


def get_data_dir() -> Path:
    """Get the data directory from environment or default to PROJECT_ROOT/data."""
    data_dir_env = os.environ.get("DATA_DIR")
    if data_dir_env:
        return Path(data_dir_env)
    return PROJECT_ROOT / "data"


@dataclass
class SessionData:
    """Data class for persisted session information."""
    session_id: str
    first_message: str | None = None
    created_at: str = ""
    turn_count: int = 0
    user_id: str | None = None  # Optional user ID for multi-user tracking

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class SessionStorage:
    """Unified session storage for both CLI and API modes.

    Stores sessions in {data_dir}/sessions.json with rich metadata including
    session ID, first message, creation time, and turn count.

    Uses in-memory caching to avoid repeated file reads when data hasn't changed.

    Args:
        data_dir: Optional data directory path. Defaults to DATA_DIR env var or PROJECT_ROOT/data.
    """

    def __init__(self, data_dir: Path | None = None):
        """Initialize session storage."""
        self._data_dir = data_dir or get_data_dir()
        self._sessions_file = self._data_dir / SESSIONS_FILENAME
        self._cache: list[dict] | None = None
        self._cache_dirty: bool = True
        self._ensure_data_dir()

    def _ensure_data_dir(self) -> None:
        """Create data directory and storage file if they don't exist."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
        if not self._sessions_file.exists():
            self._sessions_file.write_text("[]")
            logger.info(f"Created session storage: {self._sessions_file}")

    def invalidate_cache(self) -> None:
        """Invalidate the cache to force a fresh read from disk.

        Call this if the storage file may have been modified externally.
        """
        self._cache_dirty = True

    def _read_storage(self) -> list[dict]:
        """Read sessions from storage file, using cache when available."""
        if self._cache is not None and not self._cache_dirty:
            return self._cache

        try:
            content = self._sessions_file.read_text().strip()
            if not content:
                logger.warning("Storage file empty, initializing")
                return self._reset_storage()
            self._cache = json.loads(content)
            self._cache_dirty = False
            return self._cache
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted storage file: {e}, reinitializing")
            return self._reset_storage()
        except IOError as e:
            logger.error(f"IO error reading storage file: {e}")
            return []

    def _reset_storage(self) -> list[dict]:
        """Reset storage file to empty state and return empty list."""
        self._sessions_file.write_text("[]")
        self._cache = []
        self._cache_dirty = False
        return []

    def _write_storage(self, sessions: list[dict]) -> None:
        """Write sessions to storage file and update cache."""
        try:
            with open(self._sessions_file, "w") as f:
                json.dump(sessions, f, indent=2)
            self._cache = sessions
            self._cache_dirty = False
        except IOError as e:
            logger.error(f"Error writing to storage file: {e}")
            self._cache_dirty = True

    def _find_session_index(self, sessions: list[dict], session_id: str) -> int | None:
        """Find index of session by ID, or None if not found."""
        for i, session in enumerate(sessions):
            if session['session_id'] == session_id:
                return i
        return None

    def save_session(
        self,
        session_id: str,
        first_message: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Save a new session to storage.

        Args:
            session_id: Session ID to save
            first_message: Optional first message of the session
            user_id: Optional user ID for multi-user tracking
        """
        sessions = self._read_storage()

        if self._find_session_index(sessions, session_id) is not None:
            logger.debug(f"Session already exists: {session_id}")
            return

        session_data = SessionData(
            session_id=session_id,
            first_message=first_message,
            turn_count=0,
            user_id=user_id,
        )
        sessions.append(asdict(session_data))

        # Keep only last MAX_SESSIONS
        if len(sessions) > MAX_SESSIONS:
            sessions = sessions[-MAX_SESSIONS:]

        self._write_storage(sessions)
        logger.info(f"Saved session: {session_id} (user_id={user_id})")

    def load_sessions(self) -> list[SessionData]:
        """Load all sessions from storage.

        Returns:
            List of SessionData objects (newest first)
        """
        sessions = self._read_storage()
        return [SessionData(**session) for session in reversed(sessions)]

    def get_session_ids(self, user_id: str | None = None) -> list[str]:
        """Get list of session IDs (newest first).

        Args:
            user_id: Optional user ID to filter sessions

        Returns:
            List of session ID strings
        """
        sessions = self._read_storage()
        if user_id:
            sessions = [s for s in sessions if s.get('user_id') == user_id]
        return [s['session_id'] for s in reversed(sessions)]

    def get_sessions_by_user(self, user_id: str) -> list[SessionData]:
        """Get all sessions for a specific user.

        Args:
            user_id: User ID to filter by

        Returns:
            List of SessionData objects for the user (newest first)
        """
        sessions = self._read_storage()
        user_sessions = [s for s in sessions if s.get('user_id') == user_id]
        return [SessionData(**session) for session in reversed(user_sessions)]

    def get_session(self, session_id: str) -> SessionData | None:
        """Get a specific session by ID.

        Args:
            session_id: Session ID to look up

        Returns:
            SessionData if found, None otherwise
        """
        sessions = self._read_storage()
        idx = self._find_session_index(sessions, session_id)
        if idx is not None:
            return SessionData(**sessions[idx])
        return None

    def get_last_session_id(self) -> str | None:
        """Get the most recent session ID.

        Returns:
            Session ID string or None if no sessions
        """
        sessions = self._read_storage()
        if len(sessions) >= 2:
            # Return second-to-last (the previous session, not current)
            return sessions[-2]['session_id']
        return None

    def update_session(
        self,
        session_id: str,
        first_message: str | None = None,
        turn_count: int | None = None
    ) -> bool:
        """Update an existing session in storage.

        Args:
            session_id: ID of session to update
            first_message: Optional new first message
            turn_count: Optional new turn count

        Returns:
            True if session was found and updated, False otherwise
        """
        sessions = self._read_storage()
        idx = self._find_session_index(sessions, session_id)

        if idx is None:
            logger.warning(f"Session not found for update: {session_id}")
            return False

        session = sessions[idx]
        if first_message is not None and not session.get('first_message'):
            session['first_message'] = first_message
        if turn_count is not None:
            session['turn_count'] = turn_count

        self._write_storage(sessions)
        logger.debug(f"Updated session: {session_id}")
        return True

    def delete_session(self, session_id: str) -> bool:
        """Delete a session from storage.

        Args:
            session_id: ID of session to delete

        Returns:
            True if session was found and deleted, False otherwise
        """
        sessions = self._read_storage()
        initial_count = len(sessions)

        sessions = [s for s in sessions if s['session_id'] != session_id]

        if len(sessions) < initial_count:
            self._write_storage(sessions)
            logger.info(f"Deleted session: {session_id}")
            return True

        return False


@dataclass
class MessageData:
    """Data class for a single message in conversation history."""
    role: Literal["user", "assistant", "tool_use", "tool_result"]
    content: str
    timestamp: str = ""
    message_id: str | None = None
    tool_name: str | None = None  # For tool_use messages
    tool_use_id: str | None = None  # For tool_use and tool_result
    is_error: bool = False  # For tool_result
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class HistoryStorage:
    """Local storage for conversation message history.

    Stores messages in JSONL format (one JSON object per line) for efficient
    append-only writes. Each session has its own file: {data_dir}/history/{session_id}.jsonl

    Args:
        data_dir: Optional data directory path. Defaults to DATA_DIR env var or PROJECT_ROOT/data.
    """

    def __init__(self, data_dir: Path | None = None):
        """Initialize history storage."""
        self._data_dir = data_dir or get_data_dir()
        self._history_dir = self._data_dir / HISTORY_DIRNAME
        self._ensure_history_dir()

    def _ensure_history_dir(self) -> None:
        """Create history directory if it doesn't exist."""
        self._history_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"History directory ready: {self._history_dir}")

    def _get_history_file(self, session_id: str) -> Path:
        """Get the history file path for a session."""
        safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
        return self._history_dir / f"{safe_id}.jsonl"

    def append_message(
        self,
        session_id: str,
        role: Literal["user", "assistant", "tool_use", "tool_result"],
        content: str,
        message_id: str | None = None,
        tool_name: str | None = None,
        tool_use_id: str | None = None,
        is_error: bool = False,
        metadata: dict | None = None
    ) -> None:
        """Append a message to the session history.

        Args:
            session_id: Session ID
            role: Message role (user, assistant, tool_use, tool_result)
            content: Message content
            message_id: Optional message ID
            tool_name: Tool name (for tool_use messages)
            tool_use_id: Tool use ID (for tool_use and tool_result)
            is_error: Whether tool result is an error
            metadata: Additional metadata
        """
        message = MessageData(
            role=role,
            content=content,
            message_id=message_id,
            tool_name=tool_name,
            tool_use_id=tool_use_id,
            is_error=is_error,
            metadata=metadata or {}
        )

        history_file = self._get_history_file(session_id)
        try:
            with open(history_file, 'a') as f:
                f.write(json.dumps(asdict(message)) + '\n')
            logger.debug(f"Appended {role} message to {session_id}")
        except IOError as e:
            logger.error(f"Error writing to history file: {e}")

    def get_messages(self, session_id: str) -> list[MessageData]:
        """Get all messages for a session.

        Args:
            session_id: Session ID

        Returns:
            List of MessageData objects in chronological order
        """
        history_file = self._get_history_file(session_id)
        messages = []

        if not history_file.exists():
            return messages

        try:
            with open(history_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        messages.append(MessageData(**data))
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Error reading history file: {e}")

        return messages

    def get_messages_dict(self, session_id: str) -> list[dict]:
        """Get all messages as dictionaries for JSON serialization.

        Args:
            session_id: Session ID

        Returns:
            List of message dictionaries
        """
        return [asdict(msg) for msg in self.get_messages(session_id)]

    def delete_history(self, session_id: str) -> bool:
        """Delete the history file for a session.

        Args:
            session_id: Session ID

        Returns:
            True if file was deleted, False if not found
        """
        history_file = self._get_history_file(session_id)
        if history_file.exists():
            try:
                history_file.unlink()
                logger.info(f"Deleted history for session: {session_id}")
                return True
            except IOError as e:
                logger.error(f"Error deleting history file: {e}")
        return False

    def get_message_count(self, session_id: str) -> int:
        """Get the number of messages in a session history.

        Args:
            session_id: Session ID

        Returns:
            Number of messages
        """
        history_file = self._get_history_file(session_id)
        if not history_file.exists():
            return 0

        try:
            with open(history_file, 'r') as f:
                return sum(1 for line in f if line.strip())
        except IOError:
            return 0


# Global storage instances
_storage: SessionStorage | None = None
_history_storage: HistoryStorage | None = None
_configured_data_dir: Path | None = None


def configure_storage(data_dir: Path | str | None = None) -> None:
    """Configure the global data directory for storage instances.

    Call this before using get_storage() or get_history_storage() to set
    a custom data directory. If not called, DATA_DIR env var or default is used.

    Args:
        data_dir: Path to data directory. If None, uses DATA_DIR env var or default.
    """
    global _configured_data_dir, _storage, _history_storage
    _configured_data_dir = Path(data_dir) if data_dir else None
    # Reset instances to pick up new configuration
    _storage = None
    _history_storage = None


def get_storage() -> SessionStorage:
    """Get the global session storage instance."""
    global _storage
    if _storage is None:
        _storage = SessionStorage(data_dir=_configured_data_dir)
    return _storage


def get_history_storage() -> HistoryStorage:
    """Get the global history storage instance."""
    global _history_storage
    if _history_storage is None:
        _history_storage = HistoryStorage(data_dir=_configured_data_dir)
    return _history_storage
