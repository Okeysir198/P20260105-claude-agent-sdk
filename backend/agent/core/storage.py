"""Unified session storage for Claude Agent SDK.

Provides a single storage system for both CLI and API modes.
Sessions are stored in {DATA_DIR}/sessions.json with rich metadata.
Message history is stored in {DATA_DIR}/history/{session_id}.jsonl.

Configure data directory via DATA_DIR environment variable.

Per-User Storage Support:
    For multi-user deployments, use the per-user storage factory functions:
    - get_user_session_storage(username) -> data/{username}/sessions.json
    - get_user_history_storage(username) -> data/{username}/history/

    These provide complete data isolation between users.

Multi-Part Content Storage:
    Messages support both legacy string content and multi-part content formats.
    - String content: "Hello, world!"
    - Multi-part content: [{"type": "text", "text": "Hello"}, {"type": "image", "source": {...}}]

    The storage system automatically handles both formats. Content is serialized to JSON
    for storage, ensuring backward compatibility with existing string-only histories.
"""
import json
import logging
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any

from agent import PROJECT_ROOT
from core.settings import get_settings

logger = logging.getLogger(__name__)

# Get centralized settings
_settings = get_settings()

# Configuration constants (from centralized settings)
MAX_SESSIONS = _settings.storage.max_sessions
SESSIONS_FILENAME = _settings.storage.sessions_filename
HISTORY_DIRNAME = _settings.storage.history_dirname


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
    name: str | None = None  # Custom name for the session
    first_message: str | None = None
    created_at: str = ""
    turn_count: int = 0
    user_id: str | None = None  # Optional user ID for multi-user tracking
    agent_id: str | None = None  # Optional agent ID for tracking which agent is used

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
        agent_id: str | None = None,
    ) -> None:
        """Save a new session to storage.

        Args:
            session_id: Session ID to save
            first_message: Optional first message of the session
            user_id: Optional user ID for multi-user tracking
            agent_id: Optional agent ID for tracking which agent is used
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
            agent_id=agent_id,
        )
        sessions.append(asdict(session_data))

        # Keep only last MAX_SESSIONS
        if len(sessions) > MAX_SESSIONS:
            sessions = sessions[-MAX_SESSIONS:]

        self._write_storage(sessions)
        logger.info(f"Saved session: {session_id} (user_id={user_id}, agent_id={agent_id})")

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
        name: str | None = None,
        first_message: str | None = None,
        turn_count: int | None = None,
        agent_id: str | None = None,
    ) -> bool:
        """Update an existing session in storage.

        Args:
            session_id: ID of session to update
            name: Optional new custom name for the session
            first_message: Optional new first message
            turn_count: Optional new turn count
            agent_id: Optional agent ID for tracking which agent is used

        Returns:
            True if session was found and updated, False otherwise
        """
        sessions = self._read_storage()
        idx = self._find_session_index(sessions, session_id)

        if idx is None:
            logger.warning(f"Session not found for update: {session_id}")
            return False

        session = sessions[idx]
        if name is not None:  # name can be set or cleared
            session['name'] = name
        if first_message is not None and not session.get('first_message'):
            session['first_message'] = first_message
        if turn_count is not None:
            session['turn_count'] = turn_count
        if agent_id is not None:
            session['agent_id'] = agent_id

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
    """Data class for a single message in conversation history.

    Content Format:
        Supports both legacy string format and multi-part content:
        - String: "Hello, world!"
        - Multi-part: [{"type": "text", "text": "Hello"}, {"type": "image", "source": {...}}]

        The content field is typed as str | list[dict[str, Any]] to support both formats.
        When loaded from storage, string content remains a string, and multi-part content
        is deserialized from JSON back to a list of dicts.
    """
    role: str
    content: str | list[dict[str, Any]]
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
        role: str,
        content: str | list[dict[str, Any]],
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
            content: Message content (string or list of content blocks)
            message_id: Optional message ID
            tool_name: Tool name (for tool_use messages)
            tool_use_id: Tool use ID (for tool_use and tool_result)
            is_error: Whether tool result is an error
            metadata: Additional metadata

        Note:
            Multi-part content (list of dicts) is automatically serialized to JSON
            for storage and deserialized when loaded.
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


def get_user_session_storage(username: str) -> SessionStorage:
    """Get storage for user: data/{username}/sessions.json

    Args:
        username: Required. User's username for data isolation.

    Returns:
        SessionStorage instance for the user's data directory.

    Raises:
        ValueError: If username is empty or None.
    """
    if not username:
        raise ValueError("Username is required for storage access")
    user_data_dir = get_data_dir() / username
    return SessionStorage(data_dir=user_data_dir)


def get_user_history_storage(username: str) -> HistoryStorage:
    """Get storage for user: data/{username}/history/

    Args:
        username: Required. User's username for data isolation.

    Returns:
        HistoryStorage instance for the user's data directory.

    Raises:
        ValueError: If username is empty or None.
    """
    if not username:
        raise ValueError("Username is required for storage access")
    user_data_dir = get_data_dir() / username
    return HistoryStorage(data_dir=user_data_dir)


# ============================================================================
# Content Serialization Helpers
# ============================================================================

def serialize_content(content: str | list[dict[str, Any]]) -> str | list[dict[str, Any]]:
    """Prepare content for JSON serialization.

    Args:
        content: String content or list of content blocks

    Returns:
        Content ready for JSON serialization (str or list of dicts)

    Examples:
        >>> serialize_content("Hello")
        'Hello'

        >>> serialize_content([{"type": "text", "text": "Hi"}])
        [{'type': 'text', 'text': 'Hi'}]
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Convert Pydantic ContentBlock objects to dicts if needed
        serialized = []
        for block in content:
            if hasattr(block, 'model_dump'):
                # Pydantic v2
                serialized.append(block.model_dump())
            elif hasattr(block, 'dict'):
                # Pydantic v1
                serialized.append(block.dict())
            elif isinstance(block, dict):
                serialized.append(block)
            else:
                raise TypeError(f"Unsupported content block type: {type(block)}")
        return serialized
    raise TypeError(f"Unsupported content type: {type(content).__name__}")


def deserialize_content(content: Any) -> str | list[dict[str, Any]]:
    """Deserialize content from JSON storage.

    Args:
        content: Content from JSON (str, list, or dict)

    Returns:
        Deserialized content (str or list of dicts)

    Examples:
        >>> deserialize_content("Hello")
        'Hello'

        >>> deserialize_content([{"type": "text", "text": "Hi"}])
        [{'type': 'text', 'text': 'Hi'}]
    """
    # Content is already deserialized by json.loads()
    # Just validate and return as-is
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return content
    # Fallback for single dict (shouldn't happen with current MessageData structure)
    if isinstance(content, dict):
        return [content]
    raise TypeError(f"Unsupported content format: {type(content).__name__}")


def verify_multipart_storage_compatibility() -> bool:
    """Verify that the storage system can handle multi-part content.

    This function tests:
    1. String content serialization/deserialization
    2. Multi-part content serialization/deserialization
    3. Backward compatibility with existing string-only histories

    Returns:
        True if all compatibility checks pass

    Raises:
        AssertionError: If any compatibility check fails
    """
    import tempfile
    import shutil

    # Create temporary storage
    temp_dir = Path(tempfile.mkdtemp())
    try:
        storage = HistoryStorage(data_dir=temp_dir)
        test_session = "test-session-multipart"

        # Test 1: String content (backward compatibility)
        storage.append_message(
            session_id=test_session,
            role="user",
            content="Hello, world!"
        )

        # Test 2: Multi-part text content
        storage.append_message(
            session_id=test_session,
            role="user",
            content=[
                {"type": "text", "text": "First message"},
                {"type": "text", "text": "Second message"}
            ]
        )

        # Test 3: Multi-part with image
        storage.append_message(
            session_id=test_session,
            role="user",
            content=[
                {"type": "text", "text": "Analyze this:"},
                {"type": "image", "source": {"type": "url", "url": "https://example.com/img.jpg"}}
            ]
        )

        # Load and verify messages
        messages = storage.get_messages(test_session)

        assert len(messages) == 3, f"Expected 3 messages, got {len(messages)}"

        # Verify message 1: String content
        assert messages[0].content == "Hello, world!", "String content not preserved"

        # Verify message 2: Multi-part text
        assert isinstance(messages[1].content, list), "Multi-part content not preserved as list"
        assert len(messages[1].content) == 2, "Multi-part text blocks not preserved"
        assert messages[1].content[0]["text"] == "First message", "First text block not preserved"

        # Verify message 3: Multi-part with image
        assert isinstance(messages[2].content, list), "Multi-part content with image not preserved"
        assert len(messages[2].content) == 2, "Multi-part blocks not preserved"
        assert messages[2].content[1]["type"] == "image", "Image block not preserved"

        # Verify JSON serialization works
        messages_dict = storage.get_messages_dict(test_session)
        assert len(messages_dict) == 3, "get_messages_dict failed"
        assert messages_dict[0]["content"] == "Hello, world!", "Dict serialization failed for string"
        assert isinstance(messages_dict[1]["content"], list), "Dict serialization failed for multi-part"

        logger.info("Multi-part content storage verification: PASSED")
        return True

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    # Run verification when executed directly
    logging.basicConfig(level=logging.INFO)
    try:
        verify_multipart_storage_compatibility()
        print("✅ All multi-part storage compatibility checks passed!")
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        raise
