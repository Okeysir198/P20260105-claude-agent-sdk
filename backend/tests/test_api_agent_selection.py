#!/usr/bin/env python3
"""
API test for agent selection and multi-turn conversation via HTTP SSE and WebSocket.

Tests:
1. List available agents
2. Create conversation with specific agent
3. Multi-turn chat with follow-up messages

Supports two connection modes:
- HTTP SSE: Creates fresh SDK client per request with session resumption
- WebSocket: Maintains persistent SDK connection (lower latency for follow-ups)

Usage:
    # Start the server first:
    python main.py serve --port 7001

    # Run tests (default: both modes):
    python tests/test_api_agent_selection.py

    # Run specific mode:
    python tests/test_api_agent_selection.py --mode sse
    python tests/test_api_agent_selection.py --mode ws
"""
import argparse
import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import httpx
import websockets

API_BASE = "http://localhost:7001"
WS_BASE = "ws://localhost:7001"


def log(msg: str):
    """Print with immediate flush."""
    print(msg, flush=True)


@dataclass
class TurnResult:
    """Result from a single conversation turn."""
    session_id: Optional[str] = None
    sdk_session_id: Optional[str] = None
    found_in_cache: Optional[bool] = None
    text: str = ""


@dataclass
class Agent:
    """Agent information."""
    agent_id: str
    name: str


class ConversationClient(ABC):
    """Abstract base for conversation clients."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection."""
        pass

    @abstractmethod
    async def send_message(self, content: str, agent_id: Optional[str] = None) -> TurnResult:
        """Send message and get response."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connection."""
        pass


class SSEClient(ConversationClient):
    """HTTP SSE client for conversations."""

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._session_id: Optional[str] = None

    async def connect(self) -> None:
        self._client = httpx.AsyncClient(timeout=120.0)

    async def send_message(self, content: str, agent_id: Optional[str] = None) -> TurnResult:
        if not self._client:
            raise RuntimeError("Client not connected")

        result = TurnResult()

        # Determine endpoint
        if self._session_id:
            url = f"{API_BASE}/api/v1/conversations/{self._session_id}/stream"
            json_data = {"content": content}
        else:
            url = f"{API_BASE}/api/v1/conversations"
            json_data = {"content": content}
            if agent_id:
                json_data["agent_id"] = agent_id

        current_event = None

        async with self._client.stream("POST", url, json=json_data) as response:
            log(f"Status: {response.status_code}")

            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    current_event = line[6:].strip()
                elif line.startswith("data:"):
                    try:
                        data = json.loads(line[5:].strip())
                        result = self._process_sse_data(data, current_event, result)
                        if current_event in ("done", "error"):
                            break
                    except json.JSONDecodeError:
                        pass
                    current_event = None

        # Update session tracking
        if result.session_id:
            self._session_id = result.session_id

        return result

    def _process_sse_data(self, data: dict, event: Optional[str], result: TurnResult) -> TurnResult:
        """Process SSE data event."""
        if event == "done":
            log("  [done]")
        elif event == "error":
            log(f"  [error]: {data}")
        elif "session_id" in data:
            result.session_id = data["session_id"]
            result.found_in_cache = data.get("found_in_cache")
            status = "CACHED" if result.found_in_cache else "NEW"
            log(f"  Session: {result.session_id} [{status}]")
        elif "sdk_session_id" in data:
            result.sdk_session_id = data["sdk_session_id"]
            log(f"  SDK Session: {result.sdk_session_id}")
        elif "text" in data:
            result.text += data["text"]

        return result

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


class WebSocketClient(ConversationClient):
    """WebSocket client for conversations."""

    def __init__(self, agent_id: Optional[str] = None):
        self._agent_id = agent_id
        self._ws = None
        self._session_id: Optional[str] = None

    async def connect(self) -> None:
        url = f"{WS_BASE}/api/v1/ws/chat"
        if self._agent_id:
            url += f"?agent_id={self._agent_id}"

        self._ws = await websockets.connect(url)
        log(f"Status: WebSocket connected")

        # Wait for ready signal
        ready = await self._ws.recv()
        data = json.loads(ready)
        if data.get("type") != "ready":
            raise RuntimeError(f"Unexpected ready signal: {data}")
        log("  [ready]")

    async def send_message(self, content: str, agent_id: Optional[str] = None) -> TurnResult:
        if not self._ws:
            raise RuntimeError("WebSocket not connected")

        result = TurnResult()

        # Send message
        await self._ws.send(json.dumps({"content": content}))

        # Receive responses
        while True:
            msg = await self._ws.recv()
            data = json.loads(msg)

            msg_type = data.get("type")

            if msg_type == "session_id":
                result.session_id = data["session_id"]
                result.sdk_session_id = data["session_id"]
                self._session_id = result.session_id
                log(f"  Session: {result.session_id}")
            elif msg_type == "text_delta":
                result.text += data.get("text", "")
            elif msg_type == "done":
                log("  [done]")
                break
            elif msg_type == "error":
                log(f"  [error]: {data.get('error')}")
                break

        return result

    async def close(self) -> None:
        if self._ws:
            await self._ws.close()
            self._ws = None


async def get_agents() -> list[Agent]:
    """Fetch available agents from API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{API_BASE}/api/v1/config/agents")
        response.raise_for_status()
        agents = response.json().get("agents", [])
        return [Agent(agent_id=a["agent_id"], name=a["name"]) for a in agents]


async def get_history(session_id: str) -> dict:
    """Fetch session history from API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{API_BASE}/api/v1/sessions/{session_id}/history")
        response.raise_for_status()
        return response.json()


async def run_multi_turn_test(client: ConversationClient, agent: Agent, mode_name: str):
    """Run multi-turn conversation test."""
    log(f"\n{'=' * 60}")
    log(f"Multi-Turn Test ({mode_name})")
    log(f"{'=' * 60}")
    log(f"Agent: {agent.name} ({agent.agent_id})")

    await client.connect()

    try:
        # Turn 1: Initial message
        log("\n--- Turn 1: Initial message ---")
        prompt1 = "Say just 'OK' and nothing else."
        log(f'  Prompt: "{prompt1}"')
        result1 = await client.send_message(prompt1, agent_id=agent.agent_id)
        log(f'  Response: "{result1.text[:100]}"' if result1.text else "  Response: (empty)")

        session_id = result1.session_id or result1.sdk_session_id
        if not session_id:
            log("ERROR: No session_id received")
            return

        # Turn 2: Follow-up
        log("\n--- Turn 2: Follow-up message ---")
        prompt2 = "Now say just 'YES'"
        log(f'  Prompt: "{prompt2}"')
        result2 = await client.send_message(prompt2)
        log(f'  Response: "{result2.text[:100]}"' if result2.text else "  Response: (empty)")

        # Turn 3: Another follow-up
        log("\n--- Turn 3: Another follow-up ---")
        prompt3 = "Now say just 'HELLO'"
        log(f'  Prompt: "{prompt3}"')
        result3 = await client.send_message(prompt3)
        log(f'  Response: "{result3.text[:100]}"' if result3.text else "  Response: (empty)")

        # Get history (only for SSE - WebSocket uses SDK session directly)
        if isinstance(client, SSEClient) and session_id:
            log("\n--- History ---")
            history = await get_history(session_id)
            log(f"  Turn count: {history.get('turn_count', 0)}")
            log(f"  Messages: {len(history.get('messages', []))}")

    finally:
        await client.close()

    log(f"\n{'=' * 60}")
    log(f"{mode_name} test completed!")
    log(f"{'=' * 60}")


async def main():
    parser = argparse.ArgumentParser(description="API Agent Selection & Multi-Turn Test")
    parser.add_argument(
        "--mode",
        choices=["sse", "ws", "both"],
        default="both",
        help="Connection mode: sse (HTTP SSE), ws (WebSocket), or both (default)"
    )
    args = parser.parse_args()

    log("=" * 60)
    log("API Agent Selection & Multi-Turn Test")
    log("=" * 60)

    # List agents
    log("\n--- Available Agents ---")
    agents = await get_agents()
    log(f"Found {len(agents)} agents")

    if not agents:
        log("ERROR: No agents available")
        return

    agent = agents[0]
    log(f"Selected: {agent.name} ({agent.agent_id})")

    # Run tests based on mode
    if args.mode in ("sse", "both"):
        client = SSEClient()
        await run_multi_turn_test(client, agent, "HTTP SSE")

    if args.mode in ("ws", "both"):
        client = WebSocketClient(agent_id=agent.agent_id)
        await run_multi_turn_test(client, agent, "WebSocket")


if __name__ == "__main__":
    asyncio.run(main())
