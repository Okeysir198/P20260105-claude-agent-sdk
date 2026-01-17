#!/usr/bin/env python3
"""Simple test to check if resume works with real SDK ID."""
import asyncio
import httpx
from httpx_sse import aconnect_sse
import json

API_URL = "http://localhost:8888"

async def main():
    client = httpx.AsyncClient(timeout=120.0)

    print("=" * 60)
    print("SIMPLE RESUME TEST - Using Real SDK ID")
    print("=" * 60)

    # Step 1: Create a session
    print("\n[1] Creating session...")
    response = await client.post(f"{API_URL}/api/v1/sessions")
    response.raise_for_status()
    pending_id = response.json()["session_id"]
    print(f"Pending ID: {pending_id}")

    # Step 2: Send first message
    print("\n[2] Sending first message: 'My name is Alice'")
    real_sdk_id = None
    text_chunks = []

    async with aconnect_sse(
        client,
        "POST",
        f"{API_URL}/api/v1/conversations/{pending_id}/stream",
        json={"content": "My name is Alice"}
    ) as event_source:
        async for sse_event in event_source.aiter_sse():
            if sse_event.event == "session_id":
                data = json.loads(sse_event.data)
                real_sdk_id = data.get("session_id")
                print(f"✓ Real SDK ID received: {real_sdk_id}")
            elif sse_event.event == "text_delta":
                data = json.loads(sse_event.data)
                chunk = data.get("text", "")
                text_chunks.append(chunk)
                print(chunk, end="", flush=True)
            elif sse_event.event == "done":
                print("\n✓ First message complete")
                break

    if not real_sdk_id:
        print("❌ No real SDK ID received!")
        await client.aclose()
        return

    # Step 3: Resume with REAL SDK ID
    print(f"\n[3] Resuming with REAL SDK ID: {real_sdk_id}")
    response = await client.post(
        f"{API_URL}/api/v1/sessions/{real_sdk_id}/resume"
    )
    response.raise_for_status()
    print(f"✓ Resume response: {response.json()}")

    # Step 4: Send follow-up message
    print("\n[4] Sending follow-up: 'What is my name?'")
    text_chunks = []

    async with aconnect_sse(
        client,
        "POST",
        f"{API_URL}/api/v1/conversations/{real_sdk_id}/stream",
        json={"content": "What is my name?"}
    ) as event_source:
        async for sse_event in event_source.aiter_sse():
            if sse_event.event == "text_delta":
                data = json.loads(sse_event.data)
                chunk = data.get("text", "")
                text_chunks.append(chunk)
                print(chunk, end="", flush=True)
            elif sse_event.event == "done":
                print("\n✓ Second message complete")
                break

    response_text = "".join(text_chunks)

    # Check if context was maintained
    if "Alice" in response_text:
        print("\n✅ SUCCESS - Context maintained! Assistant remembered the name.")
    else:
        print(f"\n❌ FAILED - Context lost. Response: {response_text[:100]}")

    await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
