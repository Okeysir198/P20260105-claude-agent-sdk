"""Unified session storage for Claude Agent SDK.

Provides a single storage system for both CLI and API modes.
Sessions are stored in data/sessions.json with rich metadata.
"""
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from agent import PROJECT_ROOT

logger = logging.getLogger(__name__)

# Unified storage location
DATA_DIR = PROJECT_ROOT / "data"
SESSIONS_FILE = DATA_DIR / "sessions.json"
MAX_SESSIONS = 20


@dataclass
class SessionData:
    """Data class for persisted session information."""
    session_id: str
    first_message: str | None = None
    created_at: str = ""
    turn_count: int = 0

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

    def save_session(self, session_id: str, first_message: str | None = None) -> None:
        """Save a new session to storage.

        Args:
            session_id: Session ID to save
            first_message: Optional first message of the session
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
            turn_count=0
        )
        sessions.append(asdict(session_data))

        # Keep only last MAX_SESSIONS
        if len(sessions) > MAX_SESSIONS:
            sessions = sessions[-MAX_SESSIONS:]

        self._write_storage(sessions)
        logger.info(f"Saved session: {session_id}")

    def load_sessions(self) -> list[SessionData]:
        """Load all sessions from storage.

        Returns:
            List of SessionData objects (newest first)
        """
        sessions = self._read_storage()
        return [SessionData(**session) for session in reversed(sessions)]

    def get_session_ids(self) -> list[str]:
        """Get list of session IDs (newest first).

        Returns:
            List of session ID strings
        """
        sessions = self._read_storage()
        return [s['session_id'] for s in reversed(sessions)]

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


# Global storage instance
_storage: SessionStorage | None = None


def get_storage() -> SessionStorage:
    """Get the global session storage instance."""
    global _storage
    if _storage is None:
        _storage = SessionStorage()
    return _storage
