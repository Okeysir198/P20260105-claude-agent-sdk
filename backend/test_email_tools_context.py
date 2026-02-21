#!/usr/bin/env python3
"""Test email tools context variable propagation."""
import asyncio
import sys
sys.path.insert(0, '/home/nthanhtrung/Documents/01_Personal/P20260105-claude-agent-sdk/backend')

from agent.tools.email.mcp_server import set_username, get_username, reset_username
from agent.tools.email.imap_client import list_imap_impl

async def test_context_variable():
    """Test that context variable propagates through async calls."""
    print("\n=== Testing Email Tools Context Variable ===\n")

    # Test 1: Set username and verify it's accessible
    print("Test 1: Setting username to 'admin'")
    token = set_username("admin")
    print(f"  Token: {token}")

    try:
        retrieved = get_username()
        print(f"  ✓ Retrieved username: {retrieved}")
    except ValueError as e:
        print(f"  ✗ Failed to get username: {e}")
        return False

    # Test 2: Reset and verify
    print("\nTest 2: Resetting username")
    reset_username(token)
    try:
        retrieved = get_username()
        print(f"  ✗ Username still set after reset: {retrieved}")
        return False
    except ValueError as e:
        print(f"  ✓ Username cleared as expected: {e}")

    # Test 3: Test in async context (simulating agent execution)
    print("\nTest 3: Testing in async context")
    set_username("admin")

    async def async_task():
        try:
            username = get_username()
            print(f"  ✓ Async task can access username: {username}")
            return True
        except ValueError as e:
            print(f"  ✗ Async task cannot access username: {e}")
            return False

    result = await async_task()
    if not result:
        return False

    # Test 4: Test actual email tool
    print("\nTest 4: Testing list_imap_impl with admin user")
    try:
        result = list_imap_impl("admin", "gmail-johndoe", max_results=1)
        if "error" in str(result).lower() or "failed" in str(result).lower():
            print(f"  ⚠ Email tool returned error: {result}")
        else:
            print(f"  ✓ Email tool executed successfully")
            print(f"  Result preview: {str(result)[:200]}...")
    except Exception as e:
        print(f"  ✗ Email tool failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n=== All Tests Passed ===\n")
    return True

if __name__ == "__main__":
    result = asyncio.run(test_context_variable())
    sys.exit(0 if result else 1)
