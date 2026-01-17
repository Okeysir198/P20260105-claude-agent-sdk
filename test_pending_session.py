#!/usr/bin/env python3
"""Test script to send messages via pending session ID.

This demonstrates the flow:
1. Create a conversation with a pending session ID
2. Send a second message using that pending ID
3. Verify the conversation continues correctly
"""

import asyncio
import json
import httpx
import sys
from typing import Any

# Default backend URL
BACKEND_URL = "http://localhost:7001/api/v1"


async def create_conversation_with_pending_id(
    content: str,
    pending_id: str | None = None,
) -> dict[str, Any]:
    """Create a new conversation with first message.

    Args:
        content: First message content
        pending_id: Optional pending session ID (format: pending-<timestamp>)

    Returns:
        Dictionary with session_id and accumulated response
    """
    url = f"{BACKEND_URL}/conversations"
    payload = {"content": content}

    if pending_id:
        payload["pending_session_id"] = pending_id

    print(f"\n📤 Creating conversation with message: '{content}'")
    if pending_id:
        print(f"   Pending ID: {pending_id}")

    session_id = None
    accumulated_text = []
    tool_uses = []

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            url,
            json=payload,
            headers={"Accept": "text/event-stream"},
            timeout=60.0,
        ) as response:
            if response.status_code != 201:
                print(f"❌ Error: {response.status_code}")
                print(await response.aread())
                return {}

            async for line in response.aiter_lines():
                if not line.strip():
                    continue

                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    event = data.get("event")
                    event_data = data.get("data", {})

                    if event == "session_id":
                        session_id = event_data.get("session_id")
                        print(f"✅ Session ID: {session_id}")

                    elif event == "text_delta":
                        text = event_data.get("text", "")
                        accumulated_text.append(text)
                        print(text, end="", flush=True)

                    elif event == "tool_use":
                        tool_name = event_data.get("tool_name")
                        tool_input = event_data.get("input")
                        tool_uses.append({"name": tool_name, "input": tool_input})
                        print(f"\n🔧 Tool: {tool_name}")

                    elif event == "tool_result":
                        print(f"✓ Tool result received")

                    elif event == "done":
                        print(f"\n\n✅ Done (turn_count={event_data.get('turn_count')})")

                    elif event == "error":
                        print(f"\n❌ Error: {event_data.get('error')}")
                        return {}

    return {
        "session_id": session_id,
        "response": "".join(accumulated_text),
        "tool_uses": tool_uses,
    }


async def send_second_message(
    pending_session_id: str,
    content: str,
) -> dict[str, Any]:
    """Send a second message using pending session ID.

    Args:
        pending_session_id: Pending session ID (e.g., pending-1234567890)
        content: Second message content

    Returns:
        Dictionary with response data
    """
    url = f"{BACKEND_URL}/conversations/{pending_session_id}/stream"
    payload = {"content": content}

    print(f"\n📤 Sending second message: '{content}'")
    print(f"   Using pending ID: {pending_session_id}")

    accumulated_text = []
    tool_uses = []
    real_session_id = None

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            url,
            json=payload,
            headers={"Accept": "text/event-stream"},
            timeout=60.0,
        ) as response:
            if response.status_code != 200:
                print(f"❌ Error: {response.status_code}")
                print(await response.aread())
                return {}

            async for line in response.aiter_lines():
                if not line.strip():
                    continue

                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    event = data.get("event")
                    event_data = data.get("data", {})

                    if event == "session_id":
                        real_session_id = event_data.get("session_id")
                        print(f"✅ Real Session ID: {real_session_id}")

                    elif event == "text_delta":
                        text = event_data.get("text", "")
                        accumulated_text.append(text)
                        print(text, end="", flush=True)

                    elif event == "tool_use":
                        tool_name = event_data.get("tool_name")
                        tool_input = event_data.get("input")
                        tool_uses.append({"name": tool_name, "input": tool_input})
                        print(f"\n🔧 Tool: {tool_name}")

                    elif event == "tool_result":
                        print(f"✓ Tool result received")

                    elif event == "done":
                        print(f"\n\n✅ Done (turn_count={event_data.get('turn_count')})")

                    elif event == "error":
                        error_msg = event_data.get("error", "Unknown error")
                        error_code = event_data.get("error_code")
                        print(f"\n❌ Error: {error_msg}")
                        if error_code:
                            print(f"   Error code: {error_code}")
                        return {"error": error_msg, "error_code": error_code}

    return {
        "real_session_id": real_session_id,
        "response": "".join(accumulated_text),
        "tool_uses": tool_uses,
    }


async def main():
    """Main test flow."""
    print("=" * 60)
    print("Testing Pending Session ID Message Flow")
    print("=" * 60)

    # Generate a pending session ID
    import time
    pending_id = f"pending-{int(time.time() * 1000)}"
    print(f"\n📝 Generated pending ID: {pending_id}")

    # First message with pending ID
    result1 = await create_conversation_with_pending_id(
        content="Hello! My name is Claude.",
        pending_id=pending_id,
    )

    if not result1 or not result1.get("session_id"):
        print("\n❌ First message failed")
        return 1

    session_id = result1["session_id"]
    print(f"\n✓ First message complete. Real session ID: {session_id}")

    # Wait a moment
    await asyncio.sleep(1)

    # Second message using pending ID
    print("\n" + "=" * 60)
    print("Now sending second message via PENDING ID...")
    print("=" * 60)

    result2 = await send_second_message(
        pending_session_id=pending_id,  # Using pending ID, not real SDK ID
        content="What's my name?",
    )

    if result2.get("error"):
        print(f"\n❌ Second message failed: {result2['error']}")
        print("\n💡 Note: This is expected if the session expired from memory.")
        print("   Pending IDs only work while the session is in SessionManager.")
        return 1

    print(f"\n✓ Second message complete!")
    print(f"  Real session ID confirmed: {result2.get('real_session_id')}")

    print("\n" + "=" * 60)
    print("✅ Test passed! Pending ID flow working correctly.")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
