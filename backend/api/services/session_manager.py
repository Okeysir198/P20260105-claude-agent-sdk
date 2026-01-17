"""Session lifecycle management for Claude Agent SDK API."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional

from claude_agent_sdk import ClaudeSDKClient

from agent.core.agent_options import create_enhanced_options
from agent.core.storage import get_storage
from api.services.history_storage import get_history_storage
from api.services.client_pool import ClientPool, PoolClient

logger = logging.getLogger(__name__)

# Session cleanup constants
SESSION_TTL_SECONDS = 3600  # 1 hour default TTL for idle sessions
MAX_SESSIONS = 100  # Maximum number of concurrent sessions


@dataclass
class SessionState:
    """In-memory state for an active session.

    Attributes:
        session_id: Internal SessionManager key (pending-xxx for new, or real SDK ID)
        client_index: Index into ClientPool._clients list for accessing PoolClient
        real_session_id: Real SDK session ID (for history storage, may differ from session_id)
        last_accessed_at: Last time this session was accessed (for TTL cleanup)
        user_id: Optional user ID for multi-user tracking
    """

    session_id: str
    client_index: int  # Index into ClientPool._clients list
    real_session_id: Optional[str] = None  # Real SDK session ID for history storage
    user_id: Optional[str] = None  # User ID for multi-user tracking
    turn_count: int = 0
    status: Literal["active", "idle", "closed"] = "idle"
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    last_accessed_at: datetime = field(default_factory=datetime.now)  # For TTL cleanup
    first_message: Optional[str] = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class SessionManager:
    """Manages Claude SDK client sessions and their lifecycle.

    Supports multi-session mode: multiple sessions can be active simultaneously.
    Sessions are cleaned up by:
    - TTL expiry (SESSION_TTL_SECONDS)
    - Max sessions limit (MAX_SESSIONS) with LRU eviction
    - Explicit close/delete
    - Server shutdown

    Uses a ClientPool to efficiently manage SDK client connections.
    """

    def __init__(self, client_pool: ClientPool) -> None:
        """Initialize session manager.

        Args:
            client_pool: ClientPool instance for acquiring/releasing clients
        """
        self._sessions: dict[str, SessionState] = {}
        self._storage = get_storage()
        self._lock = asyncio.Lock()
        self._client_pool = client_pool
        self._instance_id = id(self)
        logger.info(f"SessionManager initialized (instance: {self._instance_id})")

    async def create_session(
        self, resume_session_id: Optional[str] = None
    ) -> SessionState:
        """Create a new session using a client from the pool.

        Args:
            resume_session_id: Optional session ID to resume

        Returns:
            SessionState for the created/resumed session

        Raises:
            RuntimeError: If client pool is exhausted
        """
        # Use resume_session_id if provided, otherwise generate a temp ID
        temp_id = resume_session_id or f"pending-{int(datetime.now().timestamp() * 1000)}"

        # Acquire client from pool
        pool_client = await self._client_pool.get_client(temp_id)

        # For resumed sessions: replace pool client with resume client
        if resume_session_id:
            logger.info(f"Replacing pool client {pool_client.index} with resume client for {resume_session_id[:20]}...")
            from claude_agent_sdk import ClaudeSDKClient

            # Disconnect old client and create new one with resume option
            # Note: disconnect may raise "cancel scope" error if client was created in different task
            try:
                await pool_client.client.disconnect()
            except Exception as e:
                logger.warning(f"Failed to disconnect old pool client {pool_client.index}: {e}")
                # Continue anyway - the old client will be garbage collected

            resume_options = create_enhanced_options(resume_session_id=resume_session_id)
            resume_client = ClaudeSDKClient(options=resume_options)
            await resume_client.connect()

            # Replace the client in the pool
            pool_client.client = resume_client
            logger.info(f"Pool client {pool_client.index} now has resume session {resume_session_id[:20]}...")

        session_state = SessionState(
            session_id=temp_id,
            client_index=self._get_pool_client_index(pool_client),
        )

        if resume_session_id:
            async with self._lock:
                self._sessions[resume_session_id] = session_state
            logger.info(
                f"Resumed session: {resume_session_id} using pool client {session_state.client_index}"
            )

        return session_state

    def _get_pool_client_index(self, pool_client) -> int:
        """Get the index of a pool client in the pool's client list.

        Args:
            pool_client: PoolClient instance

        Returns:
            Index of the client in the pool
        """
        # Access the pool's internal clients list to find the index
        for i, pc in enumerate(self._client_pool._clients):
            if pc == pool_client:
                return i
        raise RuntimeError("PoolClient not found in pool")

    async def cleanup_expired_sessions(self) -> int:
        """Remove sessions that have exceeded the TTL.

        Releases pool clients before removing sessions.

        Returns:
            Count of cleaned up sessions
        """
        now = datetime.now()
        expired_sessions: list[tuple[str, SessionState]] = []

        async with self._lock:
            for session_id, session in list(self._sessions.items()):
                elapsed = (now - session.last_accessed_at).total_seconds()
                if elapsed > SESSION_TTL_SECONDS:
                    expired_sessions.append((session_id, session))
                    del self._sessions[session_id]

        # Release pool clients outside the lock to avoid blocking
        for session_id, session in expired_sessions:
            try:
                await self._client_pool.release_client(session_id)
                logger.info(
                    f"Cleaned up expired session: {session_id} (idle for {SESSION_TTL_SECONDS}s, "
                    f"pool client {session.client_index})"
                )
            except Exception as e:
                logger.warning(f"Failed to release pool client for expired session {session_id}: {e}")

        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

        return len(expired_sessions)

    async def evict_oldest_session(self) -> Optional[str]:
        """Evict the oldest idle session when MAX_SESSIONS is reached.

        Returns:
            Session ID of evicted session, or None if no session was evicted
        """
        oldest_session: Optional[tuple[str, SessionState]] = None
        oldest_time: Optional[datetime] = None

        async with self._lock:
            # Find the oldest idle session by last_accessed_at
            for session_id, session in self._sessions.items():
                if session.status == "idle":
                    if oldest_time is None or session.last_accessed_at < oldest_time:
                        oldest_time = session.last_accessed_at
                        oldest_session = (session_id, session)

            # If no idle session found, evict the oldest active one
            if oldest_session is None:
                for session_id, session in self._sessions.items():
                    if oldest_time is None or session.last_accessed_at < oldest_time:
                        oldest_time = session.last_accessed_at
                        oldest_session = (session_id, session)

            if oldest_session:
                del self._sessions[oldest_session[0]]

        # Release pool client outside the lock
        if oldest_session:
            session_id, session = oldest_session
            try:
                await self._client_pool.release_client(session_id)
                logger.info(
                    f"Evicted oldest session: {session_id} (last accessed: {oldest_time}, "
                    f"pool client {session.client_index})"
                )
            except Exception as e:
                logger.warning(f"Failed to release pool client for evicted session {session_id}: {e}")
            return session_id

        return None

    async def register_session(
        self,
        session_id: str,
        client_index: int,
        real_session_id: Optional[str] = None,
        first_message: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> SessionState:
        """Register a session in memory.

        Args:
            session_id: Session ID (may be pending-* for new, or real SDK ID)
            client_index: Index of the pool client this session uses
            real_session_id: Real SDK session ID (for history storage)
            first_message: Optional first message to save
            user_id: Optional user ID for multi-user tracking

        Returns:
            SessionState with the client_index
        """
        # Check if we need to evict before adding a new session
        async with self._lock:
            current_count = len(self._sessions)

        if current_count >= MAX_SESSIONS:
            # First try to clean up expired sessions
            cleaned = await self.cleanup_expired_sessions()
            if cleaned == 0:
                # No expired sessions, evict the oldest one
                evicted = await self.evict_oldest_session()
                if evicted:
                    logger.info(f"Evicted session {evicted} to make room for new session")

        session_state = SessionState(
            session_id=session_id,
            client_index=client_index,
            real_session_id=real_session_id,
            user_id=user_id,
            turn_count=1 if first_message else 0,
            first_message=first_message,
        )

        async with self._lock:
            self._sessions[session_id] = session_state

        # Save to persistent storage only when we have a real session ID
        save_id = real_session_id or session_id
        if not save_id.startswith("pending-") and first_message:
            self._storage.save_session(save_id, first_message, user_id=user_id)
            logger.info(
                f"Registered session: {save_id} (user_id={user_id}, pool_client={client_index})"
            )
        else:
            logger.info(
                f"Registered pending session: {session_id} (real_id={real_session_id}, "
                f"user_id={user_id}, pool_client={client_index})"
            )

        return session_state

    async def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get an existing session by ID."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.last_accessed_at = datetime.now()
            return session

    async def find_by_session_or_real_id(self, session_id: str) -> Optional[SessionState]:
        """Find session by either session_id or real_session_id.

        Frontend sends:
        - Pending ID (pending-xxx) for follow-up messages
        - Real SDK ID (abc-123) for resumed sessions

        Args:
            session_id: Session ID to search for (could be pending-xxx or real SDK ID)

        Returns:
            SessionState if found, None otherwise
        """
        async with self._lock:
            # First try direct lookup by session_id
            if session_id in self._sessions:
                session = self._sessions[session_id]
                session.last_accessed_at = datetime.now()
                return session

            # Then search by real_session_id
            for session in self._sessions.values():
                if session.real_session_id == session_id:
                    session.last_accessed_at = datetime.now()
                    return session

        return None

    async def get_or_create_session(
        self,
        session_id: str,
        create_if_missing: bool = False,
    ) -> Optional[SessionState]:
        """Get session or create if not exists.

        Args:
            session_id: Session ID to get/create
            create_if_missing: If True, create new session if not found

        Returns:
            SessionState or None

        Raises:
            RuntimeError: If client pool is exhausted
        """
        session = await self.get_session(session_id)

        if not session and create_if_missing:
            # Acquire client from pool
            pool_client = await self._client_pool.get_client(session_id)

            session = SessionState(
                session_id=session_id,
                client_index=self._get_pool_client_index(pool_client),
            )

            async with self._lock:
                self._sessions[session_id] = session

            logger.info(
                f"Created new session: {session_id} using pool client {session.client_index}"
            )

        return session

    async def close_session(self, session_id: str) -> bool:
        """Close a session's active connection (keeps history).

        Only removes from memory, not from persistent storage.
        Use delete_session() to remove from both.

        Releases the pool client back to the pool before removing from memory.

        Args:
            session_id: ID of session to close

        Returns:
            True if session was found and closed, False otherwise
        """
        # Remove from memory only (keep in history)
        async with self._lock:
            session_state = self._sessions.pop(session_id, None)

        if session_state:
            # Release the pool client
            try:
                await self._client_pool.release_client(session_id)
                logger.info(
                    f"Released pool client {session_state.client_index} for session: {session_id}"
                )
            except Exception as e:
                logger.warning(f"Failed to release pool client for {session_id}: {e}")

            logger.info(f"Closed in-memory session: {session_id} (pool client {session_state.client_index})")
            return True

        logger.debug(f"Session not in memory: {session_id}")
        return False

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session from both memory and storage.

        Args:
            session_id: ID of session to delete

        Returns:
            True if session was found and deleted, False otherwise
        """
        # Close active connection first (releases pool client)
        await self.close_session(session_id)

        # Delete from persistent storage (sessions.json)
        deleted = self._storage.delete_session(session_id)
        if deleted:
            logger.info(f"Deleted session from storage: {session_id}")

        # Delete history file
        history_storage = get_history_storage()
        history_deleted = history_storage.delete_history(session_id)
        if history_deleted:
            logger.info(f"Deleted history file for session: {session_id}")

        return deleted or history_deleted

    async def cleanup_all(self) -> None:
        """Release all sessions and clean up (for app shutdown)."""
        async with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()

        # Release all pool clients
        for session in sessions:
            try:
                await self._client_pool.release_client(session.session_id)
            except Exception as e:
                logger.error(f"Error releasing pool client for session {session.session_id}: {e}")

        logger.info(f"Released {len(sessions)} sessions during cleanup")

    def list_sessions(self) -> list[SessionState]:
        """Get list of all active in-memory sessions."""
        return list(self._sessions.values())

    def get_session_ids(self) -> list[str]:
        """Get list of active session IDs."""
        return list(self._sessions.keys())

    def get_session_history(self) -> list[str]:
        """Get list of historical session IDs from storage."""
        return self._storage.get_session_ids()

    async def resume_session(self, session_id: str) -> SessionState:
        """Resume an existing session by ID.

        Args:
            session_id: Session ID to resume (can be pending-xxx or real SDK ID)

        Returns:
            SessionState object for the resumed session

        Raises:
            ValueError: If session cannot be resumed
        """
        # Return existing active session
        if session_id in self._sessions:
            logger.info(f"Session already active: {session_id}")
            session = self._sessions[session_id]
            session.last_accessed_at = datetime.now()
            return session

        # For pending IDs: look up the real SDK session ID from history
        # The storage session_id is the real SDK ID for resumed sessions
        resume_session_id = session_id
        if session_id.startswith("pending-"):
            # Look up in storage to find the real SDK ID
            sessions = self._storage.load_sessions()
            for session_data in reversed(sessions):  # newest first
                # Find session that matches - check various fields
                # For now, we'll use the first real session ID we find
                # In production, you might want to track pending->real mappings
                if not session_data.get('session_id', '').startswith("pending-"):
                    resume_session_id = session_data['session_id']
                    logger.info(f"Mapped pending ID {session_id} to real SDK ID {resume_session_id[:20]}...")
                    break
            else:
                raise ValueError(f"Session {session_id} not found in history")

        # For real SDK IDs: verify they exist in history
        elif session_id not in self.get_session_history():
            raise ValueError(f"Session {session_id} not found in history")

        return await self.create_session(resume_session_id=resume_session_id)

    async def update_first_message(self, session_id: str, message: str) -> bool:
        """Update the first message for a session.

        Args:
            session_id: ID of session to update
            message: First message to store

        Returns:
            True if session was found and updated
        """
        session_state = self._sessions.get(session_id)
        if session_state and not session_state.first_message:
            session_state.first_message = message
            session_state.last_accessed_at = datetime.now()
            logger.info(f"Updated first message for session: {session_id}")

        return self._storage.update_session(session_id, first_message=message)

    async def update_turn_count(self, session_id: str) -> bool:
        """Increment turn count for a session.

        Args:
            session_id: ID of session to update

        Returns:
            True if session was found and updated
        """
        session_state = self._sessions.get(session_id)
        if not session_state:
            logger.warning(f"Session not found for turn count update: {session_id}")
            return False

        session_state.turn_count += 1
        session_state.last_activity = datetime.now()
        session_state.last_accessed_at = datetime.now()

        self._storage.update_session(session_id, turn_count=session_state.turn_count)
        logger.info(
            f"Updated turn count for session {session_id}: {session_state.turn_count} "
            f"(pool client {session_state.client_index})"
        )
        return True

    def get_pool_client(self, session_id: str) -> Optional[PoolClient]:
        """Retrieve the PoolClient for a given session.

        Args:
            session_id: Session ID to get the client for

        Returns:
            PoolClient if session and pool client exist, None otherwise
        """
        session_state = self._sessions.get(session_id)
        if not session_state:
            return None

        # Get the PoolClient from the pool using the index
        pool_clients = self._client_pool._clients
        if 0 <= session_state.client_index < len(pool_clients):
            return pool_clients[session_state.client_index]

        return None
