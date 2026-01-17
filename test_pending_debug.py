#!/usr/bin/env python3
"""Debug test to see raw SSE stream."""

import asyncio
import httpx
import time

BACKEND_URL = "http://localhost:7001/api/v1"


async def test_raw_stream():
    """Test and print raw SSE stream."""
    pending_id = f"pending-{int(time.time() * 1000)}"
    print(f"Testing with pending ID: {pending_id}\n")

    print("=" * 70)
    print("RAW SSE STREAM OUTPUT")
    print("=" * 70)

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{BACKEND_URL}/conversations",
            json={"content": "Hello!", "pending_session_id": pending_id},
            headers={"Accept": "text/event-stream"},
            timeout=30.0,
        ) as response:
            print(f"Status: {response.status_code}\n")

            async for chunk in response.aiter_bytes():
                print(chunk.decode('utf-8'), end='')


if __name__ == "__main__":
    asyncio.run(test_raw_stream())
