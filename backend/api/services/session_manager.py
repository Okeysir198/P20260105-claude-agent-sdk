"""Session management service for API mode.

Provides session lifecycle management including creation, retrieval,
listing, and cleanup of conversation sessions.
"""
import asyncio
import logging
from typing import TYPE_CHECKING

from agent.core.agent_options import create_agent_sdk_options
from agent.core.session import ConversationSession
from agent.core.storage import SessionStorage, get_storage, SessionData
from api.core.errors import SessionNotFoundError

if TYPE_CHECKING:
    from api.models import SessionInfo

logger = logging.getLogger(__name__)


class SessionMetadata:
    """Metadata for a session (no SDK client, just tracking info)."""
    def __init__(self, pending_id: str, agent_id: str | None = None):
        self.pending_id = pending_id
        self.agent_id = agent_id
        self.sdk_session_id: str | None = None
        self.turn_count = 0


class SessionManager:
    """Manages conversation sessions for the API.

    Provides thread-safe session lifecycle management including creation,
    retrieval, listing, and cleanup. Uses in-memory session cache backed
    by persistent storage.

    Note: SDK clients cannot be reused across HTTP requests due to async
    context isolation. This manager only caches metadata, and creates
    fresh ConversationSession objects for each request.

    Attributes:
        _session_metadata: In-memory cache of session metadata keyed by pending ID.
        _sdk_to_pending: Mapping from SDK session ID to pending session ID.
        _storage: Persistent storage for session metadata.
        _lock: Async lock for thread-safe session operations.
    """

    PENDING_PREFIX = "pending-"

    def __init__(self):
        """Initialize the session manager."""
        self._session_metadata: dict[str, SessionMetadata] = {}
        self._sdk_to_pending: dict[str, str] = {}  # SDK ID -> pending ID mapping
        self._storage: SessionStorage = get_storage()
        self._lock = asyncio.Lock()
        # Keep _sessions for backward compatibility with lifespan cleanup
        self._sessions: dict[str, ConversationSession] = {}

    def _resolve_session_id(self, session_id: str) -> str | None:
        """Resolve a session ID to the pending ID in metadata cache.

        Supports lookup by:
        - Pending ID (pending-xxx)
        - SDK session ID (maps to pending ID via _sdk_to_pending)

        Args:
            session_id: Either a pending ID or SDK session ID.

        Returns:
            The resolved pending ID, or None if not found.
        """
        # Direct lookup first (pending ID)
        if session_id in self._session_metadata:
            return session_id

        # Try SDK ID -> pending ID mapping
        if session_id in self._sdk_to_pending:
            pending_id = self._sdk_to_pending[session_id]
            if pending_id in self._session_metadata:
                return pending_id

        return None

    def register_sdk_session_id(self, pending_id: str, sdk_session_id: str) -> None:
        """Register mapping from SDK session ID to pending ID.

        Args:
            pending_id: The API-generated pending session ID.
            sdk_session_id: The real session ID from Claude SDK.
        """
        self._sdk_to_pending[sdk_session_id] = pending_id
        # Also store on metadata
        if pending_id in self._session_metadata:
            self._session_metadata[pending_id].sdk_session_id = sdk_session_id
        logger.info(f"Registered SDK session mapping: {sdk_session_id} -> {pending_id}")

    def is_session_cached(self, session_id: str) -> bool:
        """Check if a session exists in cache.

        Args:
            session_id: Either pending ID or SDK session ID.

        Returns:
            True if session is found in cache.
        """
        return self._resolve_session_id(session_id) is not None

    def generate_pending_id(self) -> str:
        """Generate a new pending session ID.

        Returns:
            A new pending session ID with the pending- prefix.
        """
        import uuid
        return f"{self.PENDING_PREFIX}{uuid.uuid4()}"

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
        options = create_agent_sdk_options(
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

    async def get_or_create_conversation_session(
        self,
        session_id: str,
        agent_id: str | None = None
    ) -> tuple[ConversationSession, str, bool]:
        """Create a ConversationSession for the request.

        SDK clients cannot be reused across HTTP requests due to async context
        isolation. This method always creates a fresh ConversationSession, using
        cached metadata for session resumption.

        Args:
            session_id: The session identifier (pending ID or SDK session ID).
            agent_id: Optional agent ID to use when creating a new session.

        Returns:
            Tuple of (ConversationSession, resolved_session_id, found_in_cache).
        """
        async with self._lock:
            # Try to resolve existing session by pending ID or SDK ID
            resolved_id = self._resolve_session_id(session_id)

            if resolved_id is not None:
                # Found existing session metadata - create fresh session with resume
                metadata = self._session_metadata[resolved_id]

                # Create fresh session with resume option if we have sdk_session_id
                options = create_agent_sdk_options(
                    agent_id=metadata.agent_id,
                    resume_session_id=metadata.sdk_session_id
                )
                session = ConversationSession(
                    options=options,
                    include_partial_messages=True,
                    agent_id=metadata.agent_id
                )
                # Copy sdk_session_id so send_query knows this is a follow-up
                session.sdk_session_id = metadata.sdk_session_id
                session.turn_count = metadata.turn_count

                return session, resolved_id, True

            # Create new session with pending ID
            pending_id = self.generate_pending_id()

            # Store metadata (not the session object)
            self._session_metadata[pending_id] = SessionMetadata(
                pending_id=pending_id,
                agent_id=agent_id
            )

            options = create_agent_sdk_options(
                agent_id=agent_id,
                resume_session_id=None  # New session, no resume
            )
            session = ConversationSession(
                options=options,
                include_partial_messages=True,
                agent_id=agent_id
            )

            return session, pending_id, False


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
