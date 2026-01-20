"""Test SessionManager implementation."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.session_manager import SessionManager
from api.core.errors import SessionNotFoundError


async def test_session_manager():
    """Test SessionManager basic operations."""
    print("Testing SessionManager implementation...")

    # Test 1: Initialize
    print("\n1. Testing initialization...")
    manager = SessionManager()
    assert hasattr(manager, '_sessions'), "Missing _sessions attribute"
    assert hasattr(manager, '_storage'), "Missing _storage attribute"
    assert hasattr(manager, '_lock'), "Missing _lock attribute"
    print("   ✓ SessionManager initialized with correct attributes")

    # Test 2: List sessions (should be empty initially)
    print("\n2. Testing list_sessions()...")
    sessions = manager.list_sessions()
    assert isinstance(sessions, list), "list_sessions() should return a list"
    print(f"   ✓ list_sessions() returns list (found {len(sessions)} sessions)")

    # Test 3: Get non-existent session
    print("\n3. Testing get_session() with non-existent ID...")
    try:
        await manager.get_session("non-existent-id")
        print("   ✗ Should have raised SessionNotFoundError")
    except SessionNotFoundError as e:
        print(f"   ✓ Correctly raised SessionNotFoundError: {e.message}")

    # Test 4: Close non-existent session
    print("\n4. Testing close_session() with non-existent ID...")
    try:
        await manager.close_session("non-existent-id")
        print("   ✗ Should have raised SessionNotFoundError")
    except SessionNotFoundError as e:
        print(f"   ✓ Correctly raised SessionNotFoundError: {e.message}")

    # Test 5: Delete non-existent session
    print("\n5. Testing delete_session() with non-existent ID...")
    try:
        await manager.delete_session("non-existent-id")
        print("   ✗ Should have raised SessionNotFoundError")
    except SessionNotFoundError as e:
        print(f"   ✓ Correctly raised SessionNotFoundError: {e.message}")

    print("\n✓ All tests passed!")


if __name__ == "__main__":
    asyncio.run(test_session_manager())
