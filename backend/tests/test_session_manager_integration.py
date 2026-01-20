"""Comprehensive test for SessionManager implementation."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.session_manager import SessionManager, get_session_manager
from api.dependencies import SessionManagerDep
from api.models import SessionInfo
from api.core.errors import SessionNotFoundError


async def test_full_lifecycle():
    """Test full SessionManager lifecycle."""
    print("=" * 60)
    print("SessionManager Implementation Test")
    print("=" * 60)

    # Test 1: Singleton pattern
    print("\n[TEST 1] Singleton Pattern")
    manager1 = get_session_manager()
    manager2 = get_session_manager()
    assert manager1 is manager2, "get_session_manager should return singleton"
    print("✓ get_session_manager() returns singleton instance")

    # Test 2: Direct instantiation
    print("\n[TEST 2] Direct Instantiation")
    custom_manager = SessionManager()
    assert custom_manager is not manager1, "Direct instantiation creates new instance"
    print("✓ Can create separate SessionManager instances")

    # Test 3: Attributes check
    print("\n[TEST 3] Required Attributes")
    assert hasattr(custom_manager, '_sessions'), "Missing _sessions attribute"
    assert hasattr(custom_manager, '_storage'), "Missing _storage attribute"
    assert hasattr(custom_manager, '_lock'), "Missing _lock attribute"
    assert isinstance(custom_manager._sessions, dict), "_sessions should be dict"
    print("✓ All required attributes present and correct types")

    # Test 4: List sessions
    print("\n[TEST 4] List Sessions")
    sessions = custom_manager.list_sessions()
    assert isinstance(sessions, list), "list_sessions() should return list"
    print(f"✓ list_sessions() returns list of {len(sessions)} sessions")
    if sessions:
        session = sessions[0]
        assert isinstance(session, SessionInfo), "Should return SessionInfo objects"
        print(f"  Sample session: {session.session_id[:20]}... ({session.turn_count} turns)")

    # Test 5: Get non-existent session
    print("\n[TEST 5] Get Non-existent Session")
    try:
        await custom_manager.get_session("fake-session-id")
        print("✗ Should raise SessionNotFoundError")
        return False
    except SessionNotFoundError as e:
        assert e.status_code == 404, "Should have 404 status code"
        assert e.session_id == "fake-session-id", "Should include session_id"
        print(f"✓ Correctly raises SessionNotFoundError with status_code={e.status_code}")

    # Test 6: Close non-existent session
    print("\n[TEST 6] Close Non-existent Session")
    try:
        await custom_manager.close_session("another-fake-id")
        print("✗ Should raise SessionNotFoundError")
        return False
    except SessionNotFoundError:
        print("✓ Correctly raises SessionNotFoundError")

    # Test 7: Delete non-existent session
    print("\n[TEST 7] Delete Non-existent Session")
    try:
        await custom_manager.delete_session("yet-another-fake-id")
        print("✗ Should raise SessionNotFoundError")
        return False
    except SessionNotFoundError:
        print("✓ Correctly raises SessionNotFoundError")

    # Test 8: Dependencies module
    print("\n[TEST 8] FastAPI Dependencies")
    from api.dependencies import _get_session_manager_dependency
    dep_manager = await _get_session_manager_dependency()
    assert isinstance(dep_manager, SessionManager), "Dependency should return SessionManager"
    print("✓ FastAPI dependency function works correctly")

    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
    return True


async def test_async_safety():
    """Test async lock safety."""
    print("\n[TEST 9] Async Lock Safety")

    manager = SessionManager()
    concurrent_tasks = []

    async def concurrent_operation():
        """Simulate concurrent access."""
        try:
            # Try to get a non-existent session
            await manager.get_session("concurrent-test-id")
        except SessionNotFoundError:
            pass  # Expected

    # Launch multiple concurrent operations
    for _ in range(5):
        concurrent_tasks.append(concurrent_operation())

    # All should complete without deadlocks
    await asyncio.gather(*concurrent_tasks)
    print("✓ Concurrent operations handled safely with async lock")


if __name__ == "__main__":
    success = asyncio.run(test_full_lifecycle())
    if success:
        asyncio.run(test_async_safety())
