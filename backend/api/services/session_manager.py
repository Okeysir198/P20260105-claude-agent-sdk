"""Session management service for API mode.

Provides session lifecycle management including creation, retrieval,
listing, and cleanup of conversation sessions.
"""
import asyncio
import logging
from typing import TYPE_CHECKING

from agent.core.agent_options import create_enhanced_options
from agent.core.session import ConversationSession
from agent.core.storage import SessionStorage, get_storage, SessionData
from api.core.errors import SessionNotFoundError

if TYPE_CHECKING:
    from api.models import SessionInfo

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages conversation sessions for the API.

    Provides thread-safe session lifecycle management including creation,
    retrieval, listing, and cleanup. Uses in-memory session cache backed
    by persistent storage.

    Attributes:
        _sessions: In-memory cache of active sessions keyed by session ID.
        _storage: Persistent storage for session metadata.
        _lock: Async lock for thread-safe session operations.
    """

    def __init__(self):
        """Initialize the session manager."""
        self._sessions: dict[str, ConversationSession] = {}
        self._storage: SessionStorage = get_storage()
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        agent_id: str | None = None,
        resume_session_id: str | None = None
    ) -> str:
        """Create a new conversation session.

        Args:
            agent_id: Optional agent ID to load a specific agent configuration.
            resume_session_id: Optional session ID to resume.

        Returns:
            The session ID (UUID) of the created session.

        Example:
            ```python
            manager = SessionManager()
            session_id = await manager.create_session()
            session_id = await manager.create_session(agent_id="researcher")
            ```
        """
        options = create_enhanced_options(
            agent_id=agent_id,
            resume_session_id=resume_session_id
        )
        session = ConversationSession(options)
        await session.connect()

        async with self._lock:
            # Session ID will be assigned by the SDK after first message
            # For now, use a temporary UUID until we get the real one
            import uuid
            temp_id = str(uuid.uuid4())

            # Store in cache
            self._sessions[temp_id] = session

            # The real session_id will be set when the first message is sent
            # and _on_session_id is called, which updates storage

            logger.info(f"Created session: {temp_id}")
            return temp_id

    async def get_session(self, session_id: str) -> ConversationSession:
        """Get a session by ID.

        Args:
            session_id: The session ID to retrieve.

        Returns:
            The ConversationSession instance.

        Raises:
            SessionNotFoundError: If the session is not found in cache.

        Example:
            ```python
            manager = SessionManager()
            session = await manager.get_session(session_id)
            ```
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise SessionNotFoundError(session_id)
            return session

    async def close_session(self, session_id: str) -> None:
        """Close a session but keep it in storage.

        Disconnects the session client but retains the session metadata
        in storage for potential resumption.

        Args:
            session_id: The session ID to close.

        Raises:
            SessionNotFoundError: If the session is not found.

        Example:
            ```python
            manager = SessionManager()
            await manager.close_session(session_id)
            # Session remains in storage for resumption
            ```
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise SessionNotFoundError(session_id)

            await session.disconnect()
            del self._sessions[session_id]
            logger.info(f"Closed session: {session_id}")

    async def delete_session(self, session_id: str) -> None:
        """Delete a session from cache and storage.

        Disconnects the session and removes all metadata from storage.

        Args:
            session_id: The session ID to delete.

        Raises:
            SessionNotFoundError: If the session is not found.

        Example:
            ```python
            manager = SessionManager()
            await manager.delete_session(session_id)
            # Session completely removed
            ```
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise SessionNotFoundError(session_id)

            await session.disconnect()
            del self._sessions[session_id]

            # Also remove from persistent storage
            self._storage.delete_session(session_id)
            logger.info(f"Deleted session: {session_id}")

    def list_sessions(self) -> list["api.models.responses.SessionInfo"]:
        """List all sessions from storage with metadata.

        Returns:
            List of SessionInfo objects containing session metadata.

        Example:
            ```python
            manager = SessionManager()
            sessions = manager.list_sessions()
            for session_info in sessions:
                print(f"{session_info.session_id}: {session_info.turn_count} turns")
            ```
        """
        from api.models import SessionInfo

        sessions = self._storage.load_sessions()
        return [
            SessionInfo(
                session_id=s.session_id,
                created_at=s.created_at,
                turn_count=s.turn_count,
                first_message=s.first_message,
                user_id=s.user_id
            )
            for s in sessions
        ]

    async def get_or_create_conversation_session(self, session_id: str) -> ConversationSession:
        """Get existing ConversationSession or create a new one.

        This method provides thread-safe access to sessions for the SSE streaming endpoint.

        Args:
            session_id: The session identifier.

        Returns:
            ConversationSession: The existing or newly created session.
        """
        async with self._lock:
            if session_id not in self._sessions:
                # Pass session_id as resume_session_id to maintain session continuity
                options = create_enhanced_options(resume_session_id=session_id)
                session = ConversationSession(
                    options=options,
                    include_partial_messages=True
                )
                self._sessions[session_id] = session
                logger.info(f"Created new ConversationSession for: {session_id} (with resume_session_id)")
            else:
                logger.info(f"Reusing existing ConversationSession for: {session_id}")

            return self._sessions[session_id]


# Global singleton instance
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get the global SessionManager singleton instance.

    Returns:
        The global SessionManager instance.

    Example:
        ```python
        from api.services.session_manager import get_session_manager

        manager = get_session_manager()
        session_id = await manager.create_session()
        ```
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
