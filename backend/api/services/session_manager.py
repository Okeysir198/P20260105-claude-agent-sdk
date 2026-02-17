"""Session management service for API mode.

Provides session lifecycle management including creation, retrieval,
listing, and cleanup of conversation sessions.
"""
import asyncio
import logging
import uuid
from dataclasses import dataclass

from agent.core.agent_options import create_agent_sdk_options
from agent.core.session import ConversationSession
from api.core.errors import SessionNotFoundError

logger = logging.getLogger(__name__)


@dataclass
class SessionMetadata:
    """Metadata for a session (no SDK client, just tracking info)."""
    pending_id: str
    agent_id: str | None = None
    sdk_session_id: str | None = None
    turn_count: int = 0


class SessionManager:
    """Manages conversation sessions for the API.

    SDK clients cannot be reused across HTTP requests due to async context
    isolation. This manager caches metadata and creates fresh ConversationSession
    objects for each request.
    """

    PENDING_PREFIX = "pending-"

    def __init__(self):
        """Initialize the session manager."""
        self._metadata: dict[str, SessionMetadata] = {}
        self._sdk_to_pending: dict[str, str] = {}
        self._lock = asyncio.Lock()
        self._sessions: dict[str, ConversationSession] = {}

    def _resolve_session_id(self, session_id: str) -> str | None:
        """Resolve a session ID to the pending ID in metadata cache."""
        if session_id in self._metadata:
            return session_id

        if session_id in self._sdk_to_pending:
            pending_id = self._sdk_to_pending[session_id]
            if pending_id in self._metadata:
                return pending_id

        return None

    def register_sdk_session_id(self, pending_id: str, sdk_session_id: str) -> None:
        """Register mapping from SDK session ID to pending ID."""
        self._sdk_to_pending[sdk_session_id] = pending_id
        if pending_id in self._metadata:
            self._metadata[pending_id].sdk_session_id = sdk_session_id
        logger.info(f"Registered SDK session mapping: {sdk_session_id} -> {pending_id}")

    def is_session_cached(self, session_id: str) -> bool:
        """Check if a session exists in cache."""
        return self._resolve_session_id(session_id) is not None

    def generate_pending_id(self) -> str:
        """Generate a new pending session ID."""
        return f"{self.PENDING_PREFIX}{uuid.uuid4()}"

    async def create_session(
        self,
        agent_id: str | None = None,
        resume_session_id: str | None = None
    ) -> str:
        """Create a new conversation session."""
        options = create_agent_sdk_options(
            agent_id=agent_id,
            resume_session_id=resume_session_id
        )
        session = ConversationSession(options)
        await session.connect()

        async with self._lock:
            temp_id = str(uuid.uuid4())
            self._sessions[temp_id] = session
            logger.info(f"Created session: {temp_id}")
            return temp_id

    async def get_session(self, session_id: str) -> ConversationSession:
        """Get a session by ID. Raises SessionNotFoundError if not found."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise SessionNotFoundError(session_id)
            return session

    async def close_session(self, session_id: str) -> None:
        """Close and remove a session from in-memory cache.

        The session data remains in persistent storage for potential resumption.
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise SessionNotFoundError(session_id)

            await session.disconnect()
            del self._sessions[session_id]
            logger.info(f"Closed session: {session_id}")

    async def delete_session(self, session_id: str) -> None:
        """Alias for close_session (removes session from in-memory cache)."""
        await self.close_session(session_id)

    def _create_conversation_session(
        self,
        agent_id: str | None,
        resume_session_id: str | None = None
    ) -> ConversationSession:
        """Create a ConversationSession with the given parameters."""
        options = create_agent_sdk_options(
            agent_id=agent_id,
            resume_session_id=resume_session_id
        )
        return ConversationSession(
            options=options,
            include_partial_messages=True,
            agent_id=agent_id
        )

    async def get_or_create_conversation_session(
        self,
        session_id: str,
        agent_id: str | None = None
    ) -> tuple[ConversationSession, str, bool]:
        """Create a ConversationSession for the request.

        Returns tuple of (ConversationSession, resolved_session_id, found_in_cache).
        """
        async with self._lock:
            resolved_id = self._resolve_session_id(session_id)

            if resolved_id is not None:
                metadata = self._metadata[resolved_id]
                session = self._create_conversation_session(
                    agent_id=metadata.agent_id,
                    resume_session_id=metadata.sdk_session_id
                )
                session.sdk_session_id = metadata.sdk_session_id
                session.turn_count = metadata.turn_count
                return session, resolved_id, True

            pending_id = self.generate_pending_id()
            self._metadata[pending_id] = SessionMetadata(
                pending_id=pending_id,
                agent_id=agent_id
            )
            session = self._create_conversation_session(agent_id=agent_id)
            return session, pending_id, False


# Global singleton instance
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get the global SessionManager singleton instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
