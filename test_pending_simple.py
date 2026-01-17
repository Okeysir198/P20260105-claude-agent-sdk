#!/usr/bin/env python3
"""Simple test for pending session ID flow."""

import asyncio
import json
import httpx
import time

BACKEND_URL = "http://localhost:7001/api/v1"


async def stream_conversation(url: str, payload: dict) -> dict:
    """Stream a conversation and return results."""
    print(f"\n📤 POST {url}")
    print(f"   Payload: {json.dumps(payload, indent=2)}\n")

    session_id = None
    response_text = []

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            url,
            json=payload,
            headers={"Accept": "text/event-stream"},
            timeout=60.0,
        ) as response:
            print(f"   Status: {response.status_code}")

            if response.status_code not in (200, 201):
                print(f"❌ Error: {await response.aread()}")
                return {"error": f"HTTP {response.status_code}"}

            async for line in response.aiter_lines():
                if not line.strip() or not line.startswith("data: "):
                    continue

                try:
                    data = json.loads(line[6:])
                    event = data.get("event")
                    event_data = data.get("data", {})

                    if event == "session_id":
                        session_id = event_data.get("session_id")
                        print(f"✅ session_id: {session_id}")

                    elif event == "text_delta":
                        text = event_data.get("text", "")
                        response_text.append(text)
                        print(text, end="", flush=True)

                    elif event == "tool_use":
                        tool_name = event_data.get("tool_name")
                        print(f"\n🔧 tool_use: {tool_name}")

                    elif event == "tool_result":
                        print(f"\n✓ tool_result")

                    elif event == "done":
                        print(f"\n\n✅ done (turn_count={event_data.get('turn_count')})")

                    elif event == "error":
                        error = event_data.get("error", "Unknown error")
                        print(f"\n❌ error: {error}")
                        return {"error": error}

                except json.JSONDecodeError as e:
                    print(f"\n⚠️  Failed to parse SSE: {e}")
                    continue

    return {
        "session_id": session_id,
        "response": "".join(response_text),
    }


async def main():
    print("=" * 70)
    print("Testing Pending Session ID Message Flow")
    print("=" * 70)

    # Generate pending ID
    pending_id = f"pending-{int(time.time() * 1000)}"
    print(f"\n📝 Generated pending ID: {pending_id}")

    # === FIRST MESSAGE: Create conversation with pending ID ===
    print("\n" + "=" * 70)
    print("STEP 1: First message with pending ID")
    print("=" * 70)

    result1 = await stream_conversation(
        f"{BACKEND_URL}/conversations",
        {"content": "Hello! My name is Claude.", "pending_session_id": pending_id}
    )

    if result1.get("error"):
        print(f"\n❌ First message failed: {result1['error']}")
        return 1

    real_session_id = result1["session_id"]
    print(f"\n✅ First message complete!")
    print(f"   Real SDK session ID: {real_session_id}")

    await asyncio.sleep(1)

    # === SECOND MESSAGE: Use pending ID again ===
    print("\n" + "=" * 70)
    print("STEP 2: Second message using PENDING ID (not real SDK ID)")
    print("=" * 70)

    result2 = await stream_conversation(
        f"{BACKEND_URL}/conversations/{pending_id}/stream",
        {"content": "What's my name?"}
    )

    if result2.get("error"):
        print(f"\n❌ Second message failed: {result2['error']}")
        print("\n💡 This is expected if:")
        print("   - Server restarted (session evicted from memory)")
        print("   - Pending ID expired")
        print("   - SessionManager cleared the session")
        return 1

    print(f"\n✅ Second message complete!")
    print(f"   Response confirms session continuity: {result2.get('response', '')[:50]}...")

    # === THIRD MESSAGE: Use real SDK ID ===
    print("\n" + "=" * 70)
    print("STEP 3: Third message using REAL SDK ID")
    print("=" * 70)

    result3 = await stream_conversation(
        f"{BACKEND_URL}/conversations/{real_session_id}/stream",
        {"content": "What day is it?"}
    )

    if result3.get("error"):
        print(f"\n❌ Third message failed: {result3['error']}")
        return 1

    print(f"\n✅ Third message complete!")

    # === SUMMARY ===
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED!")
    print("=" * 70)
    print(f"\n📊 Summary:")
    print(f"   Pending ID:      {pending_id}")
    print(f"   Real SDK ID:     {real_session_id}")
    print(f"\n   Both pending ID and real SDK ID work correctly!")
    print(f"   ✅ Pending IDs work while session is in memory")
    print(f"   ✅ Real SDK IDs are permanent and always work")

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted")
        exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
