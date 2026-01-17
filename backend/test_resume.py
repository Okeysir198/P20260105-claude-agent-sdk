#!/usr/bin/env python3
"""Test session resume functionality with and without session ID."""
import asyncio
import httpx
from httpx_sse import aconnect_sse
import json

API_URL = "http://localhost:8888"

async def create_and_converse(client, message_content):
    """Create a session and have a conversation."""
    # Create session
    response = await client.post(f"{API_URL}/api/v1/sessions")
    response.raise_for_status()
    session_id = response.json()["session_id"]

    # Send message
    text_chunks = []
    async with aconnect_sse(
        client,
        "POST",
        f"{API_URL}/api/v1/conversations/{session_id}/stream",
        json={"content": message_content}
    ) as event_source:
        async for sse_event in event_source.aiter_sse():
            if sse_event.event == "text_delta":
                data = json.loads(sse_event.data)
                chunk = data.get("text", "")
                text_chunks.append(chunk)
            elif sse_event.event == "session_id":
                data = json.loads(sse_event.data)
                session_id = data.get("session_id")
            elif sse_event.event == "done":
                break

    return session_id, "".join(text_chunks)

async def test_resume_with_session_id(client):
    """Test resume with a specific session ID."""
    print("\n" + "=" * 60)
    print("TEST 1: RESUME WITH SESSION ID")
    print("=" * 60)

    # Step 1: Create a session and have a conversation
    print("\n[Step 1] Creating session and having initial conversation...")
    session_id, response1 = await create_and_converse(
        client,
        "My favorite color is blue. Remember this."
    )
    print(f"Session created: {session_id}")
    print(f"Response: {response1[:100]}...")

    # Step 2: Resume the session with specific ID
    print("\n[Step 2] Resuming session with ID...")
    response = await client.post(
        f"{API_URL}/api/v1/sessions/{session_id}/resume"
    )
    response.raise_for_status()
    data = response.json()
    print(f"Resume response: {data}")

    # Step 3: Send a follow-up message to test context
    print("\n[Step 3] Sending follow-up message to test context...")
    text_chunks = []
    async with aconnect_sse(
        client,
        "POST",
        f"{API_URL}/api/v1/conversations/{session_id}/stream",
        json={"content": "What's my favorite color?"}
    ) as event_source:
        async for sse_event in event_source.aiter_sse():
            if sse_event.event == "text_delta":
                data = json.loads(sse_event.data)
                chunk = data.get("text", "")
                text_chunks.append(chunk)
            elif sse_event.event == "done":
                break

    response2 = "".join(text_chunks)
    print(f"Response: {response2}")

    # Verify context was maintained
    if "blue" in response2.lower():
        print("\n✅ TEST PASSED - Context maintained after resume with ID")
        return True
    else:
        print("\n❌ TEST FAILED - Context NOT maintained")
        return False

async def test_resume_without_session_id(client):
    """Test resume without session ID (most recent)."""
    print("\n" + "=" * 60)
    print("TEST 2: RESUME WITHOUT SESSION ID (Most Recent)")
    print("=" * 60)

    # Step 1: Create a session and have a conversation
    print("\n[Step 1] Creating session...")
    session_id, response1 = await create_and_converse(
        client,
        "I love pizza. Remember this."
    )
    print(f"Session created: {session_id}")
    print(f"Response: {response1[:100]}...")

    # Step 2: Resume without session ID (should get most recent)
    print("\n[Step 2] Resuming most recent session...")
    response = await client.post(
        f"{API_URL}/api/v1/sessions/resume"
    )
    response.raise_for_status()
    data = response.json()
    resumed_session_id = data.get("session_id")
    print(f"Resumed session ID: {resumed_session_id}")

    # Verify it resumed the correct session
    if resumed_session_id == session_id:
        print("✓ Correctly resumed the most recent session")
    else:
        print(f"⚠ Warning: Expected {session_id}, got {resumed_session_id}")

    # Step 3: Send a follow-up message
    print("\n[Step 3] Sending follow-up message...")
    text_chunks = []
    async with aconnect_sse(
        client,
        "POST",
        f"{API_URL}/api/v1/conversations/{resumed_session_id}/stream",
        json={"content": "What food do I love?"}
    ) as event_source:
        async for sse_event in event_source.aiter_sse():
            if sse_event.event == "text_delta":
                data = json.loads(sse_event.data)
                chunk = data.get("text", "")
                text_chunks.append(chunk)
            elif sse_event.event == "done":
                break

    response2 = "".join(text_chunks)
    print(f"Response: {response2}")

    # Verify context
    if "pizza" in response2.lower():
        print("\n✅ TEST PASSED - Context maintained after resume without ID")
        return True
    else:
        print("\n❌ TEST FAILED - Context NOT maintained")
        return False

async def test_session_listing_after_resume(client):
    """Test that sessions are properly listed after resume."""
    print("\n" + "=" * 60)
    print("TEST 3: SESSION LISTING AFTER RESUME")
    print("=" * 60)

    # List all sessions
    print("\n[Listing all sessions...]")
    response = await client.get(f"{API_URL}/api/v1/sessions")
    response.raise_for_status()
    data = response.json()

    print(f"Total history sessions: {len(data.get('history_sessions', []))}")
    print(f"Active sessions: {len(data.get('active_sessions', []))}")

    history = data.get('history_sessions', [])
    if history:
        print(f"Most recent session: {history[0]}")
        print("\n✅ TEST PASSED - Session listing works")
        return True
    else:
        print("\n⚠ Warning - No sessions found")
        return False

async def main():
    """Run all resume tests."""
    client = httpx.AsyncClient(timeout=120.0)

    try:
        print("=" * 60)
        print("RESUME FUNCTIONALITY TEST SUITE")
        print("=" * 60)

        results = []

        # Test 1: Resume with session ID
        result1 = await test_resume_with_session_id(client)
        results.append(("Resume with ID", result1))

        # Test 2: Resume without session ID
        result2 = await test_resume_without_session_id(client)
        results.append(("Resume without ID", result2))

        # Test 3: Session listing
        result3 = await test_session_listing_after_resume(client)
        results.append(("Session listing", result3))

        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        for test_name, passed in results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status}: {test_name}")

        total_passed = sum(1 for _, passed in results if passed)
        print(f"\nTotal: {total_passed}/{len(results)} tests passed")

        if total_passed == len(results):
            print("\n🎉 ALL RESUME TESTS PASSED!")
        else:
            print("\n⚠️  SOME TESTS FAILED")

    finally:
        await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
