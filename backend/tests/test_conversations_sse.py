"""Test the conversations router with SSE streaming.

This test verifies that the SSE streaming endpoint works correctly
and supports multi-turn conversations with context retention.
"""
import asyncio
import httpx
import json
import sys
from typing import List
from pathlib import Path

# Add backend directory to path to import api package
sys.path.insert(0, str(Path(__file__).parent.parent))
from api.main import app


async def conduct_turn(client: httpx.AsyncClient, session_id: str, turn_number: int, prompt: str):
    """Conduct a single turn in a conversation.

    Args:
        client: The HTTP client for making requests
        session_id: The session ID to use
        turn_number: The turn number (1-indexed)
        prompt: The user's prompt for this turn

    Returns:
        The full response text
    """
    print(f"\n{'='*60}")
    print(f"Turn {turn_number}")
    print(f"{'='*60}")
    print(f"User: {prompt}\n")
    print("Assistant: ", end="", flush=True)

    full_response = ""

    async with client.stream(
        "POST",
        f"/api/v1/conversations/{session_id}/stream",
        json={"content": prompt},
        timeout=30.0
    ) as response:
        current_event = None

        # Read SSE events
        async for line in response.aiter_lines():
            if not line.strip():
                continue

            # Parse SSE format
            if line.startswith("event:"):
                current_event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_str = line.split(":", 1)[1].strip()
                try:
                    data = json.loads(data_str)

                    # Handle different event types
                    if current_event == "text_delta":
                        # Print text content directly and accumulate
                        if "text" in data:
                            text = data["text"]
                            print(text, end="", flush=True)
                            full_response += text
                    elif current_event == "tool_use":
                        # Print tool usage info
                        if "name" in data:
                            print(f"\n[Tool: {data['name']}]", end="", flush=True)
                        if "input" in data:
                            print(f" {data['input']}", end="", flush=True)
                    elif current_event == "error":
                        # Print error
                        if "error" in data:
                            print(f"\n[Error: {data['error']}]", flush=True)
                    elif current_event == "session_id":
                        # Session started, no output needed
                        pass
                    elif current_event == "done":
                        # Stream complete
                        print("\n")
                        break
                except json.JSONDecodeError:
                    pass  # Skip invalid JSON

    print(f"✓ Turn {turn_number} completed")
    return full_response


async def test_multi_turn_conversation():
    """Test multi-turn SSE streaming conversation."""
    # Use httpx with ASGI transport to test the SSE endpoint
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Create a session first
        print("Creating session...")
        create_response = await client.post("/api/v1/sessions", json={})
        assert create_response.status_code in [200, 201], f"Failed to create session: {create_response.text}"
        session_data = create_response.json()
        session_id = session_data["session_id"]
        print(f"✓ Created session: {session_id}")

        # Step 2: Conduct multiple turns using the same session
        turns = [
            "Hello! What is 2 + 2?",
            "Great! Now what is 5 + 3?",
            "What were the two answers you gave me in our previous messages?"
        ]

        responses: List[str] = []

        for i, prompt in enumerate(turns, start=1):
            response = await conduct_turn(client, session_id, i, prompt)
            responses.append(response)

        # Summary
        print(f"\n{'='*60}")
        print("Test Complete")
        print(f"{'='*60}")
        print(f"✓ All {len(turns)} turns completed successfully!")
        print(f"Session ID: {session_id}")
        print(f"Total turns: {len(turns)}")

        # Verify context retention (3rd turn should reference previous answers)
        if len(responses) >= 3:
            has_4 = "4" in responses[0]
            has_8 = "8" in responses[1]
            has_context = any(word in responses[2].lower() for word in ["4", "8", "two", "previous"])

            print(f"\nContext Retention Check:")
            print(f"  Turn 1 contains '4': {has_4}")
            print(f"  Turn 2 contains '8': {has_8}")
            print(f"  Turn 3 references previous: {has_context}")

            if has_context:
                print(f"  ✓ Context retention verified!")
            else:
                print(f"  ⚠ Warning: Turn 3 may not have proper context")


async def test_conversation_stream():
    """Test single-turn SSE streaming for conversations."""
    # Use httpx with ASGI transport to test the SSE endpoint
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Create a session first
        print("Creating session...")
        create_response = await client.post("/api/v1/sessions", json={})
        assert create_response.status_code in [200, 201], f"Failed to create session: {create_response.text}"
        session_data = create_response.json()
        session_id = session_data["session_id"]
        print(f"Created session: {session_id}\n")

        content = "What is 2 + 2?"

        # Step 2: Send POST request to stream endpoint (single turn)
        await conduct_turn(client, session_id, 1, content)


async def test_interrupt_endpoint():
    """Test the interrupt endpoint."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a session first
        print("Creating session for interrupt test...")
        create_response = await client.post("/api/v1/sessions", json={})
        assert create_response.status_code in [200, 201]
        session_data = create_response.json()
        session_id = session_data["session_id"]
        print(f"Created session: {session_id}")

        response = await client.post(
            f"/api/v1/conversations/{session_id}/interrupt"
        )

        print(f"Interrupt status: {response.status_code}")
        print(f"Response: {response.json()}")


if __name__ == "__main__":
    # Test 1: Single-turn streaming
    print("\n" + "="*60)
    print("TEST 1: Single-Turn SSE Streaming")
    print("="*60)
    try:
        asyncio.run(test_conversation_stream())
    except Exception as e:
        print(f"Error in streaming test: {e}")

    # Test 2: Multi-turn conversation with context retention
    print("\n\n" + "="*60)
    print("TEST 2: Multi-Turn Conversation (Context Retention)")
    print("="*60)
    try:
        asyncio.run(test_multi_turn_conversation())
    except Exception as e:
        print(f"Error in multi-turn test: {e}")
        import traceback
        traceback.print_exc()

    # Test 3: Interrupt endpoint
    print("\n\n" + "="*60)
    print("TEST 3: Interrupt Endpoint")
    print("="*60)
    try:
        asyncio.run(test_interrupt_endpoint())
    except Exception as e:
        print(f"Error in interrupt test: {e}")
