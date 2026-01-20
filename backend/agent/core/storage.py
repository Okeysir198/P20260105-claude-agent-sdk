"""Unified session storage for Claude Agent SDK.

Provides a single storage system for both CLI and API modes.
Sessions are stored in data/sessions.json with rich metadata.
Message history is stored in data/history/{session_id}.jsonl.
"""
import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Literal
from agent import PROJECT_ROOT

logger = logging.getLogger(__name__)

# Unified storage location
DATA_DIR = PROJECT_ROOT / "data"
SESSIONS_FILE = DATA_DIR / "sessions.json"
HISTORY_DIR = DATA_DIR / "history"
MAX_SESSIONS = 20


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

    Stores sessions in data/sessions.json with rich metadata including
    session ID, first message, creation time, and turn count.
    """

    def __init__(self):
        """Initialize session storage."""
        self._ensure_data_dir()

    def _ensure_data_dir(self) -> None:
        """Create data directory and storage file if they don't exist."""
        DATA_DIR.mkdir(exist_ok=True)
        if not SESSIONS_FILE.exists():
            SESSIONS_FILE.write_text("[]")
            logger.info(f"Created session storage: {SESSIONS_FILE}")

    def _read_storage(self) -> list[dict]:
        """Read sessions from storage file."""
        try:
            content = SESSIONS_FILE.read_text().strip()
            if not content:
                # File is empty, initialize it
                logger.warning("Storage file empty, initializing")
                SESSIONS_FILE.write_text("[]")
                return []
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Error reading storage file: {e}")
            # Reinitialize corrupted file
            logger.warning("Reinitializing corrupted storage file")
            SESSIONS_FILE.write_text("[]")
            return []
        except IOError as e:
            logger.error(f"IO error reading storage file: {e}")
            return []

    def _write_storage(self, sessions: list[dict]) -> None:
        """Write sessions to storage file."""
        try:
            with open(SESSIONS_FILE, 'w') as f:
                json.dump(sessions, f, indent=2)
        except IOError as e:
            logger.error(f"Error writing to storage file: {e}")

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

        # Check if session already exists
        for session in sessions:
            if session['session_id'] == session_id:
                logger.debug(f"Session already exists: {session_id}")
                return

        # Add new session
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

        for session in sessions:
            if session['session_id'] == session_id:
                if first_message is not None and not session.get('first_message'):
                    session['first_message'] = first_message
                if turn_count is not None:
                    session['turn_count'] = turn_count

                self._write_storage(sessions)
                logger.debug(f"Updated session: {session_id}")
                return True

        logger.warning(f"Session not found for update: {session_id}")
        return False

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
    append-only writes. Each session has its own file: data/history/{session_id}.jsonl
    """

    def __init__(self):
        """Initialize history storage."""
        self._ensure_history_dir()

    def _ensure_history_dir(self) -> None:
        """Create history directory if it doesn't exist."""
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        logger.debug(f"History directory ready: {HISTORY_DIR}")

    def _get_history_file(self, session_id: str):
        """Get the history file path for a session."""
        # Sanitize session_id to prevent path traversal
        safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
        return HISTORY_DIR / f"{safe_id}.jsonl"

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


def get_storage() -> SessionStorage:
    """Get the global session storage instance."""
    global _storage
    if _storage is None:
        _storage = SessionStorage()
    return _storage


def get_history_storage() -> HistoryStorage:
    """Get the global history storage instance."""
    global _history_storage
    if _history_storage is None:
        _history_storage = HistoryStorage()
    return _history_storage
