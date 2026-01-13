"""Session lifecycle management for Claude Agent SDK API."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional

from claude_agent_sdk import ClaudeSDKClient

from agent.core.agent_options import create_enhanced_options
from agent.core.storage import get_storage, SessionData

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """In-memory state for an active session."""

    session_id: str
    client: ClaudeSDKClient
    turn_count: int = 0
    status: Literal["active", "idle", "closed"] = "idle"
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    first_message: Optional[str] = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class SessionManager:
    """Manages Claude SDK client sessions and their lifecycle.

    Uses __aenter__()/__aexit__() pattern for proper async context management.
    """

    def __init__(self):
        """Initialize session manager."""
        self._sessions: dict[str, SessionState] = {}
        self._storage = get_storage()
        self._lock = asyncio.Lock()
        self._instance_id = id(self)
        logger.info(f"SessionManager initialized (instance: {self._instance_id})")

    async def create_session(self, resume_session_id: Optional[str] = None) -> SessionState:
        """Create a new session using connect() for proper initialization.

        Args:
            resume_session_id: Optional session ID to resume

        Returns:
            SessionState for the created/resumed session
        """
        options = create_enhanced_options(resume_session_id=resume_session_id)
        client = ClaudeSDKClient(options)

        # Use connect() to properly initialize the client
        await client.connect()

        session_state = SessionState(
            session_id=resume_session_id or "",
            client=client,
            turn_count=0,
            status="idle",
            created_at=datetime.now(),
            last_activity=datetime.now()
        )

        if resume_session_id:
            async with self._lock:
                self._sessions[resume_session_id] = session_state
            logger.info(f"Resumed session: {resume_session_id}")

        return session_state

    async def register_session(self, session_id: str, client: ClaudeSDKClient, first_message: Optional[str] = None) -> SessionState:
        """Register a session in memory.

        Args:
            session_id: Session ID (may be pending-* or real SDK ID)
            client: The ClaudeSDKClient (already connected)
            first_message: Optional first message to save

        Returns:
            SessionState with the persisted client
        """
        session_state = SessionState(
            session_id=session_id,
            client=client,
            turn_count=1 if first_message else 0,
            status="idle",
            created_at=datetime.now(),
            last_activity=datetime.now(),
            first_message=first_message
        )

        async with self._lock:
            self._sessions[session_id] = session_state

        # Only save to persistent storage if it's a real session ID (not pending-*)
        if not session_id.startswith("pending-") and first_message:
            self._storage.save_session(session_id, first_message)
        logger.info(f"Registered session: {session_id}")

        return session_state

    async def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get an existing session by ID.

        Args:
            session_id: ID of session to retrieve

        Returns:
            SessionState if found, None otherwise
        """
        async with self._lock:
            return self._sessions.get(session_id)

    async def close_session(self, session_id: str) -> bool:
        """Close a session using disconnect() for proper cleanup.

        Also removes from persistent storage.

        Args:
            session_id: ID of session to close

        Returns:
            True if session was found and closed (from memory or storage), False otherwise
        """
        found_in_memory = False
        found_in_storage = False

        # Try to close in-memory session
        async with self._lock:
            session_state = self._sessions.get(session_id)
            if session_state:
                found_in_memory = True
                del self._sessions[session_id]

        # Disconnect client if found in memory
        if found_in_memory and session_state:
            try:
                await session_state.client.disconnect()
                logger.info(f"Closed in-memory session: {session_id}")
            except Exception as e:
                logger.error(f"Error closing session {session_id}: {e}")

        # Also delete from persistent storage
        found_in_storage = self._storage.delete_session(session_id)
        if found_in_storage:
            logger.info(f"Deleted session from storage: {session_id}")

        if not found_in_memory and not found_in_storage:
            logger.warning(f"Session not found for closing: {session_id}")
            return False

        return True

    async def cleanup_all(self):
        """Close all sessions (for app shutdown)."""
        async with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()

        for session in sessions:
            try:
                await session.client.disconnect()
            except Exception as e:
                logger.error(f"Error closing session {session.session_id}: {e}")

    def list_sessions(self) -> list[SessionState]:
        """
        Get list of all active in-memory sessions.

        Returns:
            List of SessionState objects
        """
        return list(self._sessions.values())

    def list_active_sessions(self) -> list[str]:
        """
        Get list of active session IDs.

        Returns:
            List of session ID strings
        """
        return list(self._sessions.keys())

    def get_session_history(self) -> list[str]:
        """
        Get list of historical session IDs from storage.

        Returns:
            List of session ID strings
        """
        return self._storage.get_session_ids()

    async def resume_session(self, session_id: str) -> SessionState:
        """
        Resume an existing session by ID.

        Args:
            session_id: Session ID to resume

        Returns:
            SessionState object for the resumed session

        Raises:
            ValueError: If session cannot be resumed
        """
        # Check if already active
        if session_id in self._sessions:
            logger.info(f"Session already active: {session_id}")
            return self._sessions[session_id]

        # Check if exists in history
        history = self.get_session_history()
        if session_id not in history:
            raise ValueError(f"Session {session_id} not found in history")

        # Create new session with resume option
        session_state = await self.create_session(resume_session_id=session_id)
        return session_state

    async def update_session_id(self, old_id: str, new_id: str, first_message: Optional[str] = None) -> bool:
        """Update session with real ID from SDK.

        Args:
            old_id: Temporary session ID (pending-*)
            new_id: Real session ID from SDK
            first_message: Optional first message to store

        Returns:
            True if updated successfully
        """
        async with self._lock:
            session_state = self._sessions.pop(old_id, None)
            if session_state:
                session_state.session_id = new_id
                session_state.first_message = first_message
                self._sessions[new_id] = session_state
                # Save to persistent storage
                self._storage.save_session(new_id, first_message)
                logger.info(f"Updated session ID: {old_id} -> {new_id}")
                return True
        return False

    async def update_first_message(self, session_id: str, message: str) -> bool:
        """
        Update the first message for a session.

        Updates both in-memory and persisted storage.

        Args:
            session_id: ID of session to update
            message: First message to store

        Returns:
            True if session was found and updated, False otherwise
        """
        # Update in-memory session
        session_state = self._sessions.get(session_id)
        if session_state and not session_state.first_message:
            session_state.first_message = message
            logger.info(f"Updated first message for session: {session_id}")

        # Update persisted storage
        return self._storage.update_session(session_id, first_message=message)

    async def update_turn_count(self, session_id: str) -> bool:
        """
        Increment turn count for a session.

        Updates both in-memory and persisted storage.

        Args:
            session_id: ID of session to update

        Returns:
            True if session was found and updated, False otherwise
        """
        # Update in-memory session
        session_state = self._sessions.get(session_id)
        if session_state:
            session_state.turn_count += 1
            session_state.last_activity = datetime.now()

            # Update persisted storage
            self._storage.update_session(
                session_id,
                turn_count=session_state.turn_count
            )

            logger.info(f"Updated turn count for session {session_id}: {session_state.turn_count}")
            return True

        logger.warning(f"Session not found for turn count update: {session_id}")
        return False
