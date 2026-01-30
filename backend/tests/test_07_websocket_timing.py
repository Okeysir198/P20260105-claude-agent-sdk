#!/usr/bin/env python3
"""
Timing test: WebSocket vs HTTP SSE TTFT comparison.

Requires server: python main.py serve --port 7001
Run: python tests/test_07_websocket_timing.py [--websocket-only|--http-only] [--turns N]
"""
import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Load .env from backend directory
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import httpx
import websockets

API_BASE = "http://localhost:7001"
WS_BASE = "ws://localhost:7001"
API_KEY = os.getenv("API_KEY")

# User credentials for WebSocket authentication - loaded from environment
DEFAULT_USERNAME = os.getenv("CLI_USERNAME", "admin")
DEFAULT_PASSWORD = os.getenv("CLI_ADMIN_PASSWORD")

if not API_KEY:
    print("ERROR: API_KEY not set. Create .env file with API_KEY=your_key", file=sys.stderr)
    sys.exit(1)

if not DEFAULT_PASSWORD:
    print("ERROR: CLI_ADMIN_PASSWORD not set. Create .env file with CLI_ADMIN_PASSWORD=your_password", file=sys.stderr)
    sys.exit(1)


def log(msg: str) -> None:
    print(msg, flush=True)


async def get_jwt_token() -> str:
    """Get JWT token via user login.

    Logs in with username/password to get a user_identity token
    required for WebSocket authentication.
    """
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
    }
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        response = await client.post(
            f"{API_BASE}/api/v1/auth/login",
            json={
                "username": DEFAULT_USERNAME,
                "password": DEFAULT_PASSWORD,
            }
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("success"):
            raise RuntimeError(f"Login failed: {data.get('error')}")
        return data["token"]


async def test_http_sse(num_turns: int = 3) -> list[float]:
    """Test HTTP SSE endpoints (with reconnection per request).

    Each HTTP request creates a fresh SDK client and uses resume_session_id
    to continue the conversation context.
    """
    log("\n=== HTTP SSE (with reconnection) ===\n")

    headers = {"X-API-Key": API_KEY} if API_KEY else {}

    async with httpx.AsyncClient(timeout=120.0, headers=headers) as client:
        # Get an agent
        response = await client.get(f"{API_BASE}/api/v1/config/agents")
        agent = response.json()["agents"][0]
        agent_id = agent["agent_id"]

        session_id = None
        times = []

        for turn in range(1, num_turns + 1):
            prompt = f"Say just the number {turn}"

            start = time.perf_counter()
            first_token_time = None

            url = f"{API_BASE}/api/v1/conversations"
            data = {"content": prompt, "agent_id": agent_id}
            if session_id:
                url = f"{API_BASE}/api/v1/conversations/{session_id}/stream"
                data = {"content": prompt}

            async with client.stream("POST", url, json=data) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        try:
                            d = json.loads(line[5:].strip())
                            if "session_id" in d:
                                session_id = d["session_id"]
                            if "text" in d and first_token_time is None:
                                first_token_time = time.perf_counter()
                        except json.JSONDecodeError:
                            pass
                    elif line.startswith("event:"):
                        if "done" in line or "error" in line:
                            break

            end = time.perf_counter()
            ttft = (first_token_time - start) * 1000 if first_token_time else 0
            total = (end - start) * 1000
            times.append(ttft)

            session_type = "NEW" if turn == 1 else "RESUME"
            log(f"Turn {turn} [{session_type}]: TTFT={ttft:.0f}ms, Total={total:.0f}ms")

        return times


async def test_websocket(num_turns: int = 3) -> list[float]:
    """Test WebSocket endpoint (persistent connection).

    The SDK client is created once and maintained for all turns,
    keeping the same async context throughout.
    """
    log("\n=== WebSocket (persistent connection) ===\n")

    # Get JWT token and an agent
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    async with httpx.AsyncClient(timeout=120.0, headers=headers) as client:
        response = await client.get(f"{API_BASE}/api/v1/config/agents")
        agent = response.json()["agents"][0]
        agent_id = agent["agent_id"]

    jwt_token = await get_jwt_token()

    times = []
    connect_start = time.perf_counter()

    ws_url = f"{WS_BASE}/api/v1/ws/chat?token={jwt_token}&agent_id={agent_id}"

    async with websockets.connect(ws_url) as ws:
        connect_time = (time.perf_counter() - connect_start) * 1000
        log(f"WebSocket connect: {connect_time:.0f}ms")

        # Wait for ready signal
        ready = await ws.recv()
        ready_data = json.loads(ready)
        if ready_data.get("type") != "ready":
            log(f"Unexpected ready signal: {ready_data}")
            return []

        for turn in range(1, num_turns + 1):
            prompt = f"Say just the number {turn}"

            start = time.perf_counter()
            first_token_time = None

            # Send message
            await ws.send(json.dumps({"content": prompt}))

            # Receive responses
            while True:
                msg = await ws.recv()
                data = json.loads(msg)

                if data.get("type") == "text_delta" and first_token_time is None:
                    first_token_time = time.perf_counter()
                elif data.get("type") == "done":
                    break
                elif data.get("type") == "error":
                    log(f"Error: {data}")
                    break

            end = time.perf_counter()
            ttft = (first_token_time - start) * 1000 if first_token_time else 0
            total = (end - start) * 1000
            times.append(ttft)

            log(f"Turn {turn}: TTFT={ttft:.0f}ms, Total={total:.0f}ms")

    return times


def print_summary(http_times: list[float], ws_times: list[float]) -> None:
    """Print comparison summary."""
    log("\n" + "=" * 60)
    log("SUMMARY")
    log("=" * 60)
    log("\n| Turn | HTTP SSE (reconnect) | WebSocket (persistent) | Savings |")
    log("|------|---------------------|------------------------|---------|")

    num_turns = max(len(http_times), len(ws_times))
    for i in range(num_turns):
        http_t = http_times[i] if i < len(http_times) else 0
        ws_t = ws_times[i] if i < len(ws_times) else 0
        savings = http_t - ws_t
        log(f"| {i+1}    | {http_t:.0f}ms              | {ws_t:.0f}ms                 | {savings:.0f}ms    |")

    if len(http_times) >= 2 and len(ws_times) >= 2:
        avg_http_followup = sum(http_times[1:]) / len(http_times[1:])
        avg_ws_followup = sum(ws_times[1:]) / len(ws_times[1:])
        log(f"\nAverage follow-up TTFT:")
        log(f"  HTTP SSE:   {avg_http_followup:.0f}ms")
        log(f"  WebSocket:  {avg_ws_followup:.0f}ms")
        if avg_http_followup > 0:
            savings_pct = (avg_http_followup - avg_ws_followup) / avg_http_followup * 100
            log(f"  Savings:    {avg_http_followup - avg_ws_followup:.0f}ms ({savings_pct:.0f}% faster)")


async def main() -> None:
    parser = argparse.ArgumentParser(description="WebSocket vs HTTP SSE timing comparison")
    parser.add_argument("--websocket-only", action="store_true", help="Run WebSocket test only")
    parser.add_argument("--http-only", action="store_true", help="Run HTTP SSE test only")
    parser.add_argument("--turns", type=int, default=3, help="Number of conversation turns")
    args = parser.parse_args()

    log("=" * 60)
    log("WebSocket vs HTTP SSE Timing Comparison")
    log("=" * 60)

    http_times = []
    ws_times = []

    if not args.websocket_only:
        http_times = await test_http_sse(args.turns)

    if not args.http_only:
        ws_times = await test_websocket(args.turns)

    # Print summary if both tests ran
    if http_times and ws_times:
        print_summary(http_times, ws_times)
    elif ws_times:
        log("\n" + "=" * 60)
        log("WebSocket Results")
        log("=" * 60)
        avg = sum(ws_times[1:]) / len(ws_times[1:]) if len(ws_times) > 1 else ws_times[0]
        log(f"Average follow-up TTFT: {avg:.0f}ms")
    elif http_times:
        log("\n" + "=" * 60)
        log("HTTP SSE Results")
        log("=" * 60)
        avg = sum(http_times[1:]) / len(http_times[1:]) if len(http_times) > 1 else http_times[0]
        log(f"Average follow-up TTFT: {avg:.0f}ms")


if __name__ == "__main__":
    asyncio.run(main())
