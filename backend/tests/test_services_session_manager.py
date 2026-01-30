"""Comprehensive unit tests for SessionManager service.

Tests all methods including session lifecycle, cache management, eviction,
and singleton pattern.
"""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.core.errors import SessionNotFoundError
from api.services.session_manager import (
    MAX_SESSIONS,
    SESSION_TTL_SECONDS,
    SessionManager,
    SessionMetadata,
    get_session_manager,
)


class TestSessionMetadata:
    """Test SessionMetadata dataclass."""

    def test_session_metadata_creation(self):
        """Test creating SessionMetadata with all fields."""
        metadata = SessionMetadata(
            pending_id="pending-123",
            agent_id="agent-abc",
            sdk_session_id="sdk-xyz",
            turn_count=5,
            last_accessed=1234567890.0
        )

        assert metadata.pending_id == "pending-123"
        assert metadata.agent_id == "agent-abc"
        assert metadata.sdk_session_id == "sdk-xyz"
        assert metadata.turn_count == 5
        assert metadata.last_accessed == 1234567890.0

    def test_session_metadata_defaults(self):
        """Test SessionMetadata with default values."""
        before_time = time.time()
        metadata = SessionMetadata(pending_id="pending-default")
        after_time = time.time()

        assert metadata.pending_id == "pending-default"
        assert metadata.agent_id is None
        assert metadata.sdk_session_id is None
        assert metadata.turn_count == 0
        assert before_time <= metadata.last_accessed <= after_time


class TestSessionManagerInit:
    """Test SessionManager initialization."""

    def test_init_creates_empty_state(self):
        """Test that __init__ initializes all data structures."""
        manager = SessionManager()

        assert isinstance(manager._metadata, dict)
        assert len(manager._metadata) == 0

        assert isinstance(manager._sdk_to_pending, dict)
        assert len(manager._sdk_to_pending) == 0

        assert isinstance(manager._sessions, dict)
        assert len(manager._sessions) == 0

        assert isinstance(manager._lock, asyncio.Lock)

    def test_pending_prefix_constant(self):
        """Test PENDING_PREFIX constant."""
        assert SessionManager.PENDING_PREFIX == "pending-"


class TestResolveSessionId:
    """Test _resolve_session_id method."""

    def test_resolve_pending_id_directly_in_metadata(self):
        """Test resolving when session_id is already in _metadata."""
        manager = SessionManager()
        pending_id = "pending-abc123"
        manager._metadata[pending_id] = SessionMetadata(pending_id=pending_id)

        result = manager._resolve_session_id(pending_id)

        assert result == pending_id

    def test_resolve_sdk_session_id(self):
        """Test resolving SDK session ID through mapping."""
        manager = SessionManager()
        pending_id = "pending-xyz789"
        sdk_id = "sdk-session-123"

        manager._metadata[pending_id] = SessionMetadata(
            pending_id=pending_id,
            sdk_session_id=sdk_id
        )
        manager._sdk_to_pending[sdk_id] = pending_id

        result = manager._resolve_session_id(sdk_id)

        assert result == pending_id

    def test_resolve_sdk_session_id_when_pending_not_in_metadata(self):
        """Test resolving SDK ID when pending ID was evicted."""
        manager = SessionManager()
        sdk_id = "sdk-session-456"
        pending_id = "pending-evicted"

        # Only have mapping, not metadata (evicted scenario)
        manager._sdk_to_pending[sdk_id] = pending_id

        result = manager._resolve_session_id(sdk_id)

        assert result is None

    def test_resolve_unknown_session_id(self):
        """Test resolving unknown session ID returns None."""
        manager = SessionManager()

        result = manager._resolve_session_id("unknown-id")

        assert result is None


class TestRegisterSdkSessionId:
    """Test register_sdk_session_id method."""

    def test_register_sdk_session_id_creates_mapping(self):
        """Test registering creates SDK to pending mapping."""
        manager = SessionManager()
        pending_id = "pending-abc"
        sdk_id = "sdk-123"

        manager.register_sdk_session_id(pending_id, sdk_id)

        assert manager._sdk_to_pending[sdk_id] == pending_id

    def test_register_sdk_session_id_updates_metadata(self):
        """Test registering updates metadata with SDK session ID."""
        manager = SessionManager()
        pending_id = "pending-def"
        sdk_id = "sdk-456"

        manager._metadata[pending_id] = SessionMetadata(
            pending_id=pending_id,
            sdk_session_id=None
        )

        manager.register_sdk_session_id(pending_id, sdk_id)

        assert manager._metadata[pending_id].sdk_session_id == sdk_id

    def test_register_sdk_session_id_when_metadata_not_exists(self):
        """Test registering when metadata doesn't exist yet."""
        manager = SessionManager()
        pending_id = "pending-ghi"
        sdk_id = "sdk-789"

        # Should not raise error
        manager.register_sdk_session_id(pending_id, sdk_id)

        assert manager._sdk_to_pending[sdk_id] == pending_id
        # Metadata not created, so no update happens
        assert pending_id not in manager._metadata


class TestIsSessionCached:
    """Test is_session_cached method."""

    def test_is_session_cached_with_pending_id(self):
        """Test checking cache with pending ID."""
        manager = SessionManager()
        pending_id = "pending-test"

        manager._metadata[pending_id] = SessionMetadata(pending_id=pending_id)

        assert manager.is_session_cached(pending_id) is True

    def test_is_session_cached_with_sdk_id(self):
        """Test checking cache with SDK session ID."""
        manager = SessionManager()
        pending_id = "pending-sdk-test"
        sdk_id = "-sdk-session"

        manager._metadata[pending_id] = SessionMetadata(
            pending_id=pending_id,
            sdk_session_id=sdk_id
        )
        manager._sdk_to_pending[sdk_id] = pending_id

        assert manager.is_session_cached(sdk_id) is True

    def test_is_session_cached_not_found(self):
        """Test checking cache for non-existent session."""
        manager = SessionManager()

        assert manager.is_session_cached("unknown") is False


class TestGeneratePendingId:
    """Test generate_pending_id method."""

    def test_generate_pending_id_format(self):
        """Test generated ID has correct format."""
        manager = SessionManager()

        pending_id = manager.generate_pending_id()

        assert pending_id.startswith(SessionManager.PENDING_PREFIX)
        # After prefix, should have a UUID (36 chars for standard UUID)
        assert len(pending_id) == len(SessionManager.PENDING_PREFIX) + 36

    def test_generate_pending_id_unique(self):
        """Test each generated ID is unique."""
        manager = SessionManager()

        ids = [manager.generate_pending_id() for _ in range(100)]

        assert len(set(ids)) == 100  # All unique


class TestEvictStaleSessions:
    """Test _evict_stale_sessions method."""

    def test_evict_old_sessions_by_ttl(self):
        """Test eviction removes sessions older than TTL."""
        manager = SessionManager()
        current_time = time.time()

        # Add old session (older than TTL)
        old_id = "pending-old"
        manager._metadata[old_id] = SessionMetadata(
            pending_id=old_id,
            sdk_session_id="sdk-old",
            last_accessed=current_time - SESSION_TTL_SECONDS - 100
        )

        # Add fresh session
        fresh_id = "pending-fresh"
        manager._metadata[fresh_id] = SessionMetadata(
            pending_id=fresh_id,
            sdk_session_id="sdk-fresh",
            last_accessed=current_time
        )

        manager._sdk_to_pending["sdk-old"] = old_id
        manager._sdk_to_pending["sdk-fresh"] = fresh_id

        manager._evict_stale_sessions()

        assert old_id not in manager._metadata
        assert fresh_id in manager._metadata
        assert "sdk-old" not in manager._sdk_to_pending
        assert "sdk-fresh" in manager._sdk_to_pending

    def test_evict_when_exceeding_max_sessions(self):
        """Test eviction removes oldest sessions when exceeding MAX_SESSIONS."""
        manager = SessionManager()
        current_time = time.time()

        # Create MAX_SESSIONS + 10 sessions
        num_sessions = MAX_SESSIONS + 10
        session_ids = []

        for i in range(num_sessions):
            session_id = f"pending-{i}"
            session_ids.append(session_id)
            manager._metadata[session_id] = SessionMetadata(
                pending_id=session_id,
                last_accessed=current_time - (num_sessions - i)  # Older sessions first
            )

        # Evict should remove oldest 10
        manager._evict_stale_sessions()

        assert len(manager._metadata) == MAX_SESSIONS
        # Oldest sessions should be removed
        for i in range(10):
            assert f"pending-{i}" not in manager._metadata
        # Newest sessions should remain
        for i in range(10, num_sessions):
            assert f"pending-{i}" in manager._metadata

    def test_evict_removes_sdk_mapping(self):
        """Test eviction also removes SDK session ID mapping."""
        manager = SessionManager()
        current_time = time.time()

        old_id = "pending-old-sdk"
        sdk_id = "old-sdk-session"

        manager._metadata[old_id] = SessionMetadata(
            pending_id=old_id,
            sdk_session_id=sdk_id,
            last_accessed=current_time - SESSION_TTL_SECONDS - 1
        )
        manager._sdk_to_pending[sdk_id] = old_id

        manager._evict_stale_sessions()

        assert sdk_id not in manager._sdk_to_pending

    def test_evict_handles_session_without_sdk_id(self):
        """Test eviction handles sessions without SDK session ID."""
        manager = SessionManager()
        current_time = time.time()

        old_id = "pending-no-sdk"

        manager._metadata[old_id] = SessionMetadata(
            pending_id=old_id,
            sdk_session_id=None,
            last_accessed=current_time - SESSION_TTL_SECONDS - 1
        )

        manager._evict_stale_sessions()

        assert old_id not in manager._metadata

    def test_evict_when_under_limit_and_all_fresh(self):
        """Test eviction does nothing when under limit and all sessions fresh."""
        manager = SessionManager()
        current_time = time.time()

        session_id = "pending-fresh-only"
        manager._metadata[session_id] = SessionMetadata(
            pending_id=session_id,
            last_accessed=current_time
        )

        manager._evict_stale_sessions()

        assert session_id in manager._metadata


class TestCreateSession:
    """Test create_session method."""

    @patch("api.services.session_manager.ConversationSession")
    @patch("api.services.session_manager.create_agent_sdk_options")
    async def test_create_session_with_defaults(self, mock_create_options, mock_session_class):
        """Test creating session with default parameters."""
        manager = SessionManager()
        mock_session = AsyncMock()
        mock_session_class.return_value = mock_session
        mock_options = MagicMock()
        mock_create_options.return_value = mock_options

        session_id = await manager.create_session()

        assert isinstance(session_id, str)
        assert session_id in manager._sessions
        mock_create_options.assert_called_once_with(agent_id=None, resume_session_id=None)
        mock_session_class.assert_called_once_with(mock_options)
        mock_session.connect.assert_called_once()

    @patch("api.services.session_manager.ConversationSession")
    @patch("api.services.session_manager.create_agent_sdk_options")
    async def test_create_session_with_agent_id(self, mock_create_options, mock_session_class):
        """Test creating session with agent ID."""
        manager = SessionManager()
        mock_session = AsyncMock()
        mock_session_class.return_value = mock_session
        mock_options = MagicMock()
        mock_create_options.return_value = mock_options

        agent_id = "agent-test-123"

        await manager.create_session(agent_id=agent_id)

        mock_create_options.assert_called_once_with(agent_id=agent_id, resume_session_id=None)

    @patch("api.services.session_manager.ConversationSession")
    @patch("api.services.session_manager.create_agent_sdk_options")
    async def test_create_session_with_resume_id(self, mock_create_options, mock_session_class):
        """Test creating session with resume session ID."""
        manager = SessionManager()
        mock_session = AsyncMock()
        mock_session_class.return_value = mock_session
        mock_options = MagicMock()
        mock_create_options.return_value = mock_options

        resume_id = "resume-abc-456"

        await manager.create_session(resume_session_id=resume_id)

        mock_create_options.assert_called_once_with(agent_id=None, resume_session_id=resume_id)

    @patch("api.services.session_manager.ConversationSession")
    @patch("api.services.session_manager.create_agent_sdk_options")
    async def test_create_session_calls_eviction(self, mock_create_options, mock_session_class):
        """Test create_session triggers eviction before creation."""
        manager = SessionManager()
        mock_session = AsyncMock()
        mock_session_class.return_value = mock_session
        mock_options = MagicMock()
        mock_create_options.return_value = mock_options

        with patch.object(manager, "_evict_stale_sessions") as mock_evict:
            await manager.create_session()

            mock_evict.assert_called_once()

    @patch("api.services.session_manager.ConversationSession")
    @patch("api.services.session_manager.create_agent_sdk_options")
    async def test_create_session_unique_ids(self, mock_create_options, mock_session_class):
        """Test each create_session returns unique ID."""
        manager = SessionManager()
        mock_session = AsyncMock()
        mock_session_class.return_value = mock_session
        mock_options = MagicMock()
        mock_create_options.return_value = mock_options

        ids = [await manager.create_session() for _ in range(10)]

        assert len(set(ids)) == 10  # All unique


class TestGetSession:
    """Test get_session method."""

    async def test_get_existing_session(self):
        """Test getting an existing session."""
        manager = SessionManager()
        session_id = "test-session-123"
        mock_session = MagicMock()
        manager._sessions[session_id] = mock_session

        with patch.object(manager, "_evict_stale_sessions"):
            result = await manager.get_session(session_id)

        assert result is mock_session

    async def test_get_nonexistent_session_raises_error(self):
        """Test getting non-existent session raises SessionNotFoundError."""
        manager = SessionManager()

        with pytest.raises(SessionNotFoundError) as exc_info:
            await manager.get_session("nonexistent")

        assert "nonexistent" in str(exc_info.value)

    async def test_get_session_calls_eviction(self):
        """Test get_session triggers eviction."""
        manager = SessionManager()
        session_id = "test-session"
        mock_session = MagicMock()
        manager._sessions[session_id] = mock_session

        with patch.object(manager, "_evict_stale_sessions") as mock_evict:
            await manager.get_session(session_id)

            mock_evict.assert_called_once()


class TestCloseSession:
    """Test close_session method."""

    async def test_close_existing_session(self):
        """Test closing an existing session."""
        manager = SessionManager()
        session_id = "close-test"
        mock_session = AsyncMock()
        manager._sessions[session_id] = mock_session

        await manager.close_session(session_id)

        mock_session.disconnect.assert_called_once()
        assert session_id not in manager._sessions

    async def test_close_nonexistent_session_raises_error(self):
        """Test closing non-existent session raises SessionNotFoundError."""
        manager = SessionManager()

        with pytest.raises(SessionNotFoundError) as exc_info:
            await manager.close_session("nonexistent-close")

        assert "nonexistent-close" in str(exc_info.value)


class TestDeleteSession:
    """Test delete_session method."""

    async def test_delete_existing_session(self):
        """Test deleting an existing session."""
        manager = SessionManager()
        session_id = "delete-test"
        mock_session = AsyncMock()
        manager._sessions[session_id] = mock_session

        await manager.delete_session(session_id)

        mock_session.disconnect.assert_called_once()
        assert session_id not in manager._sessions

    async def test_delete_nonexistent_session_raises_error(self):
        """Test deleting non-existent session raises SessionNotFoundError."""
        manager = SessionManager()

        with pytest.raises(SessionNotFoundError) as exc_info:
            await manager.delete_session("nonexistent-delete")

        assert "nonexistent-delete" in str(exc_info.value)


class TestCreateConversationSession:
    """Test _create_conversation_session method."""

    @patch("api.services.session_manager.ConversationSession")
    @patch("api.services.session_manager.create_agent_sdk_options")
    def test_create_conversation_session_defaults(self, mock_create_options, mock_session_class):
        """Test creating conversation session with defaults."""
        manager = SessionManager()
        mock_options = MagicMock()
        mock_create_options.return_value = mock_options
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        result = manager._create_conversation_session(
            agent_id=None,
            resume_session_id=None
        )

        mock_create_options.assert_called_once_with(agent_id=None, resume_session_id=None)
        mock_session_class.assert_called_once_with(
            options=mock_options,
            include_partial_messages=True,
            agent_id=None
        )
        assert result is mock_session

    @patch("api.services.session_manager.ConversationSession")
    @patch("api.services.session_manager.create_agent_sdk_options")
    def test_create_conversation_session_with_agent(self, mock_create_options, mock_session_class):
        """Test creating conversation session with agent ID."""
        manager = SessionManager()
        mock_options = MagicMock()
        mock_create_options.return_value = mock_options
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        agent_id = "test-agent-xyz"

        manager._create_conversation_session(agent_id=agent_id)

        mock_create_options.assert_called_once_with(agent_id=agent_id, resume_session_id=None)
        mock_session_class.assert_called_once_with(
            options=mock_options,
            include_partial_messages=True,
            agent_id=agent_id
        )

    @patch("api.services.session_manager.ConversationSession")
    @patch("api.services.session_manager.create_agent_sdk_options")
    def test_create_conversation_session_with_resume(self, mock_create_options, mock_session_class):
        """Test creating conversation session with resume ID."""
        manager = SessionManager()
        mock_options = MagicMock()
        mock_create_options.return_value = mock_options
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        resume_id = "resume-session-abc"

        manager._create_conversation_session(
            agent_id=None,
            resume_session_id=resume_id
        )

        mock_create_options.assert_called_once_with(agent_id=None, resume_session_id=resume_id)


class TestGetOrCreateConversationSession:
    """Test get_or_create_conversation_session method."""

    @patch("api.services.session_manager.ConversationSession")
    @patch("api.services.session_manager.create_agent_sdk_options")
    async def test_get_existing_cached_session(self, mock_create_options, mock_session_class):
        """Test getting existing session from cache."""
        manager = SessionManager()
        pending_id = "pending-cached"
        sdk_id = "sdk-cached"
        agent_id = "agent-cached"
        turn_count = 5

        manager._metadata[pending_id] = SessionMetadata(
            pending_id=pending_id,
            agent_id=agent_id,
            sdk_session_id=sdk_id,
            turn_count=turn_count
        )

        mock_options = MagicMock()
        mock_create_options.return_value = mock_options
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        session, resolved_id, found = await manager.get_or_create_conversation_session(
            pending_id
        )

        assert found is True
        assert resolved_id == pending_id
        assert session is mock_session
        assert session.sdk_session_id == sdk_id
        assert session.turn_count == turn_count
        mock_create_options.assert_called_once_with(
            agent_id=agent_id,
            resume_session_id=sdk_id
        )

    @patch("api.services.session_manager.ConversationSession")
    @patch("api.services.session_manager.create_agent_sdk_options")
    async def test_get_existing_cached_session_updates_last_accessed(
        self, mock_create_options, mock_session_class
    ):
        """Test getting cached session updates last_accessed timestamp."""
        manager = SessionManager()
        pending_id = "pending-timestamp"
        old_time = time.time() - 1000

        manager._metadata[pending_id] = SessionMetadata(
            pending_id=pending_id,
            last_accessed=old_time
        )

        mock_options = MagicMock()
        mock_create_options.return_value = mock_options
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        await manager.get_or_create_conversation_session(pending_id)

        assert manager._metadata[pending_id].last_accessed > old_time

    @patch("api.services.session_manager.ConversationSession")
    @patch("api.services.session_manager.create_agent_sdk_options")
    async def test_create_new_session(self, mock_create_options, mock_session_class):
        """Test creating new session when not cached."""
        manager = SessionManager()
        agent_id = "new-agent"

        mock_options = MagicMock()
        mock_create_options.return_value = mock_options
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        session, resolved_id, found = await manager.get_or_create_conversation_session(
            "nonexistent",
            agent_id=agent_id
        )

        assert found is False
        assert resolved_id.startswith(SessionManager.PENDING_PREFIX)
        assert resolved_id in manager._metadata
        assert session is mock_session
        assert manager._metadata[resolved_id].agent_id == agent_id
        mock_create_options.assert_called_once_with(agent_id=agent_id, resume_session_id=None)

    @patch("api.services.session_manager.ConversationSession")
    @patch("api.services.session_manager.create_agent_sdk_options")
    async def test_resolves_via_sdk_id(self, mock_create_options, mock_session_class):
        """Test resolving session via SDK session ID."""
        manager = SessionManager()
        pending_id = "pending-via-sdk"
        sdk_id = "resolve-me"

        manager._metadata[pending_id] = SessionMetadata(
            pending_id=pending_id,
            sdk_session_id=sdk_id
        )
        manager._sdk_to_pending[sdk_id] = pending_id

        mock_options = MagicMock()
        mock_create_options.return_value = mock_options
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        session, resolved_id, found = await manager.get_or_create_conversation_session(sdk_id)

        assert found is True
        assert resolved_id == pending_id

    @patch("api.services.session_manager.ConversationSession")
    @patch("api.services.session_manager.create_agent_sdk_options")
    async def test_calls_eviction_before_lookup(self, mock_create_options, mock_session_class):
        """Test eviction is called before lookup/creation."""
        manager = SessionManager()

        mock_options = MagicMock()
        mock_create_options.return_value = mock_options
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        with patch.object(manager, "_evict_stale_sessions") as mock_evict:
            await manager.get_or_create_conversation_session("test-id")

            mock_evict.assert_called_once()


class TestGetSessionManagerSingleton:
    """Test get_session_manager singleton pattern."""

    def test_get_session_manager_returns_instance(self):
        """Test get_session_manager returns SessionManager instance."""
        manager = get_session_manager()

        assert isinstance(manager, SessionManager)

    def test_get_session_manager_returns_same_instance(self):
        """Test get_session_manager returns same instance on subsequent calls."""
        manager1 = get_session_manager()
        manager2 = get_session_manager()

        assert manager1 is manager2

    def test_get_session_manager_lazily_initializes(self):
        """Test singleton is created only on first call."""
        # Reset global singleton
        import api.services.session_manager as sm_module
        original_singleton = sm_module._session_manager
        sm_module._session_manager = None

        try:
            # Verify singleton is None before first call
            assert sm_module._session_manager is None

            manager = get_session_manager()

            # After call, singleton is set
            assert sm_module._session_manager is not None
            assert sm_module._session_manager is manager
        finally:
            # Restore original singleton
            sm_module._session_manager = original_singleton


class TestSessionManagerConcurrency:
    """Test SessionManager behavior with concurrent operations."""

    @patch("api.services.session_manager.ConversationSession")
    @patch("api.services.session_manager.create_agent_sdk_options")
    async def test_concurrent_session_creation(self, mock_create_options, mock_session_class):
        """Test multiple concurrent session creations."""
        manager = SessionManager()
        mock_session = AsyncMock()
        mock_session_class.return_value = mock_session
        mock_options = MagicMock()
        mock_create_options.return_value = mock_options

        # Create 10 sessions concurrently
        tasks = [manager.create_session() for _ in range(10)]
        session_ids = await asyncio.gather(*tasks)

        assert len(set(session_ids)) == 10  # All unique
        assert len(manager._sessions) == 10

    @patch("api.services.session_manager.ConversationSession")
    @patch("api.services.session_manager.create_agent_sdk_options")
    async def test_concurrent_get_or_create_same_session(self, mock_create_options, mock_session_class):
        """Test concurrent get_or_create for same session ID."""
        manager = SessionManager()

        mock_options = MagicMock()
        mock_create_options.return_value = mock_options
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        session_id = "concurrent-test"

        # Try to get/create same session concurrently
        tasks = [
            manager.get_or_create_conversation_session(session_id)
            for _ in range(5)
        ]
        results = await asyncio.gather(*tasks)

        # All should return different pending IDs (new sessions each time)
        resolved_ids = [r[1] for r in results]
        assert len(set(resolved_ids)) == 5  # All different

    @patch("api.services.session_manager.ConversationSession")
    @patch("api.services.session_manager.create_agent_sdk_options")
    async def test_lock_prevents_race_condition(self, mock_create_options, mock_session_class):
        """Test that lock prevents race conditions."""
        manager = SessionManager()

        mock_options = MagicMock()
        mock_create_options.return_value = mock_options
        mock_session = AsyncMock()
        mock_session_class.return_value = mock_session

        # Create a cached session first
        pending_id = "pending-locked"
        manager._metadata[pending_id] = SessionMetadata(
            pending_id=pending_id,
            agent_id="agent-1"
        )

        # Multiple concurrent reads
        tasks = [
            manager.get_or_create_conversation_session(pending_id)
            for _ in range(10)
        ]
        results = await asyncio.gather(*tasks)

        # All should find the cached session
        for session, resolved_id, found in results:
            assert found is True
            assert resolved_id == pending_id


class TestSessionManagerEdgeCases:
    """Test edge cases and boundary conditions."""

    async def test_close_and_delete_session_after_eviction(self):
        """Test closing/deleting session that was evicted."""
        manager = SessionManager()

        # Session is not in _sessions (evicted or never existed)
        with pytest.raises(SessionNotFoundError):
            await manager.close_session("evicted-session")

        with pytest.raises(SessionNotFoundError):
            await manager.delete_session("evicted-session")

    def test_resolve_empty_string_session_id(self):
        """Test resolving empty string session ID."""
        manager = SessionManager()

        result = manager._resolve_session_id("")

        assert result is None

    def test_is_session_cached_with_empty_string(self):
        """Test is_session_cached with empty string."""
        manager = SessionManager()

        result = manager.is_session_cached("")

        assert result is False

    @patch("api.services.session_manager.ConversationSession")
    @patch("api.services.session_manager.create_agent_sdk_options")
    async def test_get_or_create_with_none_agent_id(self, mock_create_options, mock_session_class):
        """Test get_or_create with None agent_id."""
        manager = SessionManager()

        mock_options = MagicMock()
        mock_create_options.return_value = mock_options
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        session, resolved_id, found = await manager.get_or_create_conversation_session(
            "test-session",
            agent_id=None
        )

        assert found is False
        assert resolved_id in manager._metadata
        assert manager._metadata[resolved_id].agent_id is None

    @patch("api.services.session_manager.ConversationSession")
    @patch("api.services.session_manager.create_agent_sdk_options")
    async def test_multiple_evictions_in_sequence(self, mock_create_options, mock_session_class):
        """Test multiple eviction cycles."""
        manager = SessionManager()
        current_time = time.time()

        # Create sessions with staggered ages
        for i in range(MAX_SESSIONS + 20):
            session_id = f"pending-{i}"
            manager._metadata[session_id] = SessionMetadata(
                pending_id=session_id,
                last_accessed=current_time - (MAX_SESSIONS + 20 - i) * 10
            )

        # First eviction
        manager._evict_stale_sessions()
        first_count = len(manager._metadata)

        # Second eviction (should be stable if no new sessions added)
        manager._evict_stale_sessions()
        second_count = len(manager._metadata)

        assert first_count == second_count
        assert first_count <= MAX_SESSIONS
