#!/usr/bin/env python3
"""Test sending second message immediately after first."""

import asyncio
import httpx
import time
import json

BACKEND_URL = "http://localhost:7001/api/v1"

async def main():
    pending_id = f"pending-{int(time.time() * 1000)}"
    print(f"Pending ID: {pending_id}")

    # First message
    print("\n=== First message ===")
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{BACKEND_URL}/conversations",
            json={"content": "Hello!", "pending_session_id": pending_id},
            headers={"Accept": "text/event-stream"},
            timeout=30.0,
        ) as response:
            raw = await response.aread()
            print(raw.decode('utf-8')[:500])

    # IMMEDIATE second message (no delay)
    print("\n=== Second message (IMMEDIATE) ===")
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{BACKEND_URL}/conversations/{pending_id}/stream",
            json={"content": "What's my name?"},
            headers={"Accept": "text/event-stream"},
            timeout=30.0,
        ) as response:
            raw = await response.aread()
            print(raw.decode('utf-8')[:500])

asyncio.run(main())
