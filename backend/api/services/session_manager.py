"""Session management service for API mode.

Provides session lifecycle management including creation, retrieval,
listing, and cleanup of conversation sessions.
"""
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field

from agent.core.agent_options import create_agent_sdk_options
from agent.core.session import ConversationSession
from api.core.errors import SessionNotFoundError

logger = logging.getLogger(__name__)

# Session eviction configuration
MAX_SESSIONS = 100
SESSION_TTL_SECONDS = 3600  # 1 hour


@dataclass
class SessionMetadata:
    """Metadata for a session (no SDK client, just tracking info)."""
    pending_id: str
    agent_id: str | None = None
    sdk_session_id: str | None = None
    turn_count: int = 0
    last_accessed: float = field(default_factory=time.time)


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

    def _evict_stale_sessions(self) -> None:
        """Remove sessions older than TTL or when exceeding MAX_SESSIONS.

        Eviction strategy:
        1. Remove sessions older than SESSION_TTL_SECONDS
        2. If still exceeding MAX_SESSIONS, remove oldest sessions first
        """
        current_time = time.time()
        sessions_to_remove: list[str] = []

        # Step 1: Remove sessions older than TTL
        for session_id, metadata in self._metadata.items():
            if current_time - metadata.last_accessed > SESSION_TTL_SECONDS:
                sessions_to_remove.append(session_id)

        # Remove stale sessions
        for session_id in sessions_to_remove:
            metadata = self._metadata[session_id]
            del self._metadata[session_id]
            if metadata.sdk_session_id and metadata.sdk_session_id in self._sdk_to_pending:
                del self._sdk_to_pending[metadata.sdk_session_id]
            logger.info(f"Evicted stale session: {session_id} (age: {current_time - metadata.last_accessed:.0f}s)")

        # Step 2: If still exceeding MAX_SESSIONS, remove oldest
        if len(self._metadata) > MAX_SESSIONS:
            # Sort sessions by last_accessed (oldest first)
            sorted_sessions = sorted(
                self._metadata.items(),
                key=lambda x: x[1].last_accessed
            )

            # Calculate how many to remove
            excess_count = len(self._metadata) - MAX_SESSIONS

            # Remove oldest sessions
            for session_id, metadata in sorted_sessions[:excess_count]:
                del self._metadata[session_id]
                if metadata.sdk_session_id and metadata.sdk_session_id in self._sdk_to_pending:
                    del self._sdk_to_pending[metadata.sdk_session_id]
                logger.info(f"Evicted session due to MAX_SESSIONS limit: {session_id}")

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
            # Evict stale sessions before creating new one
            self._evict_stale_sessions()

            temp_id = str(uuid.uuid4())
            self._sessions[temp_id] = session
            logger.info(f"Created session: {temp_id}")
            return temp_id

    async def get_session(self, session_id: str) -> ConversationSession:
        """Get a session by ID. Raises SessionNotFoundError if not found."""
        async with self._lock:
            # Evict stale sessions on access
            self._evict_stale_sessions()

            session = self._sessions.get(session_id)
            if session is None:
                raise SessionNotFoundError(session_id)
            return session

    async def close_session(self, session_id: str) -> None:
        """Close a session but keep it in storage for potential resumption."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise SessionNotFoundError(session_id)

            await session.disconnect()
            del self._sessions[session_id]
            logger.info(f"Closed session: {session_id}")

    async def delete_session(self, session_id: str) -> None:
        """Delete a session from in-memory cache."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise SessionNotFoundError(session_id)

            await session.disconnect()
            del self._sessions[session_id]
            logger.info(f"Deleted session: {session_id}")

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
            # Evict stale sessions before lookup/creation
            self._evict_stale_sessions()

            resolved_id = self._resolve_session_id(session_id)

            if resolved_id is not None:
                metadata = self._metadata[resolved_id]
                # Update last_accessed timestamp
                metadata.last_accessed = time.time()
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
