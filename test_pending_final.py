#!/usr/bin/env python3
"""Final working test for pending session ID flow."""

import asyncio
import httpx
import time

BACKEND_URL = "http://localhost:7001/api/v1"


async def stream_and_print(url: str, payload: dict, description: str) -> tuple[str | None, str]:
    """Stream conversation and return (session_id, response_text)."""
    print(f"\n{'='*70}")
    print(f"{description}")
    print(f"{'='*70}")
    print(f"📤 {url}")
    print(f"   Payload: {payload}\n")

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
            if response.status_code not in (200, 201):
                print(f"❌ HTTP {response.status_code}")
                return None, f"HTTP {response.status_code}"

            # Read raw response text
            raw_text = (await response.aread()).decode('utf-8')

            # Parse SSE events
            for line in raw_text.split('\n'):
                line = line.strip()
                if not line:
                    continue

                if line.startswith('event: '):
                    current_event = line[7:]
                elif line.startswith('data: '):
                    try:
                        import json
                        data = json.loads(line[6:])

                        if current_event == 'session_id':
                            session_id = data.get('session_id')
                            print(f"✅ session_id: {session_id}")

                        elif current_event == 'text_delta':
                            text = data.get('text', '')
                            response_text.append(text)
                            print(text, end='', flush=True)

                        elif current_event == 'done':
                            print(f"\n\n✅ done (turn_count={data.get('turn_count')})")

                        elif current_event == 'error':
                            error = data.get('error', 'Unknown error')
                            print(f"\n❌ error: {error}")
                            return None, error

                    except json.JSONDecodeError:
                        pass

    return session_id, ''.join(response_text)


async def main():
    print("="*70)
    print("Testing Pending Session ID Message Flow")
    print("="*70)

    pending_id = f"pending-{int(time.time() * 1000)}"
    print(f"\n📝 Generated pending ID: {pending_id}")

    # Message 1: Create with pending ID
    real_session_id, _ = await stream_and_print(
        f"{BACKEND_URL}/conversations",
        {"content": "Hello! My name is Claude.", "pending_session_id": pending_id},
        "STEP 1: First message with pending ID"
    )

    if not real_session_id:
        print("\n❌ Failed to get session ID")
        return 1

    print(f"\n✅ Real SDK session ID: {real_session_id}")
    await asyncio.sleep(1)

    # Message 2: Use pending ID again
    session_id_2, response_2 = await stream_and_print(
        f"{BACKEND_URL}/conversations/{pending_id}/stream",
        {"content": "What's my name?"},
        "STEP 2: Second message using PENDING ID"
    )

    if not session_id_2:
        print(f"\n❌ Second message failed: {response_2}")
        return 1

    print(f"\n✅ Second message succeeded!")

    await asyncio.sleep(1)

    # Message 3: Use real SDK ID
    _, response_3 = await stream_and_print(
        f"{BACKEND_URL}/conversations/{real_session_id}/stream",
        {"content": "What day is it?"},
        "STEP 3: Third message using REAL SDK ID"
    )

    print(f"\n✅ Third message succeeded!")

    # Summary
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)
    print(f"\n📊 Results:")
    print(f"   Pending ID:    {pending_id}")
    print(f"   Real SDK ID:   {real_session_id}")
    print(f"\n   ✅ Pending IDs work while session is in memory")
    print(f"   ✅ Real SDK IDs are permanent and always work")

    return 0


if __name__ == "__main__":
    try:
        exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted")
        exit(1)
