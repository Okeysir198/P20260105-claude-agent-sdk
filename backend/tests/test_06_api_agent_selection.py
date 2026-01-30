#!/usr/bin/env python3
"""
API test: Agent selection and multi-turn chat via HTTP SSE and WebSocket.

Requires server: python main.py serve --port 7001
Run: python tests/test_06_api_agent_selection.py [--mode sse|ws|both]
"""
import argparse
import asyncio
import json
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import httpx
import websockets

from core.settings import get_settings

settings = get_settings()
API_BASE = os.getenv("TEST_API_URL", f"http://{settings.api.host}:{settings.api.port}")
WS_BASE = os.getenv("TEST_WS_URL", f"ws://{settings.api.host}:{settings.api.port}")
API_KEY = os.getenv("API_KEY")
DEFAULT_USERNAME = os.getenv("CLI_USERNAME", "admin")
DEFAULT_PASSWORD = os.getenv("CLI_ADMIN_PASSWORD")

if not API_KEY:
    print("ERROR: API_KEY not set", file=sys.stderr)
    sys.exit(1)

if not DEFAULT_PASSWORD:
    print("ERROR: CLI_ADMIN_PASSWORD not set", file=sys.stderr)
    sys.exit(1)


def log(msg: str) -> None:
    print(msg, flush=True)


@dataclass
class TurnResult:
    session_id: Optional[str] = None
    text: str = ""


class ConversationClient(ABC):
    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def send_message(self, content: str, agent_id: Optional[str] = None) -> TurnResult: ...

    @abstractmethod
    async def close(self) -> None: ...


class SSEClient(ConversationClient):
    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None
        self._session_id: Optional[str] = None

    async def connect(self) -> None:
        headers = {"X-API-Key": API_KEY}
        self._client = httpx.AsyncClient(timeout=120.0, headers=headers)

    async def send_message(self, content: str, agent_id: Optional[str] = None) -> TurnResult:
        if not self._client:
            raise RuntimeError("Client not connected")

        result = TurnResult()
        url = f"{API_BASE}/api/v1/conversations/{self._session_id}/stream" if self._session_id else f"{API_BASE}/api/v1/conversations"
        json_data = {"content": content}
        if agent_id and not self._session_id:
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
                        if "session_id" in data:
                            result.session_id = data["session_id"]
                            log(f"  Session: {result.session_id}")
                        elif "text" in data:
                            result.text += data["text"]
                        if current_event in ("done", "error"):
                            break
                    except json.JSONDecodeError:
                        pass
                    current_event = None

        if result.session_id:
            self._session_id = result.session_id
        return result

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()


class WebSocketClient(ConversationClient):
    def __init__(self, agent_id: Optional[str] = None) -> None:
        self._agent_id = agent_id
        self._ws = None
        self._jwt_token: Optional[str] = None

    async def connect(self) -> None:
        self._jwt_token = await self._get_user_token()
        url = f"{WS_BASE}/api/v1/ws/chat?token={self._jwt_token}"
        if self._agent_id:
            url += f"&agent_id={self._agent_id}"

        self._ws = await websockets.connect(url)
        log("Status: WebSocket connected")

        ready = await self._ws.recv()
        if json.loads(ready).get("type") != "ready":
            raise RuntimeError(f"Unexpected ready signal")
        log("  [ready]")

    async def send_message(self, content: str, agent_id: Optional[str] = None) -> TurnResult:
        if not self._ws:
            raise RuntimeError("WebSocket not connected")

        result = TurnResult()
        await self._ws.send(json.dumps({"content": content}))

        while True:
            msg = await self._ws.recv()
            data = json.loads(msg)
            msg_type = data.get("type")

            if msg_type == "session_id":
                result.session_id = data["session_id"]
                log(f"  Session: {result.session_id}")
            elif msg_type == "text_delta":
                result.text += data.get("text", "")
            elif msg_type in ("done", "error"):
                log(f"  [{msg_type}]")
                break

        return result

    async def close(self) -> None:
        if self._ws:
            await self._ws.close()

    async def _get_user_token(self) -> str:
        headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.post(
                f"{API_BASE}/api/v1/auth/login",
                json={"username": DEFAULT_USERNAME, "password": DEFAULT_PASSWORD}
            )
            response.raise_for_status()
            return response.json()["token"]


async def get_agents() -> list[dict]:
    headers = {"X-API-Key": API_KEY}
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        response = await client.get(f"{API_BASE}/api/v1/config/agents")
        response.raise_for_status()
        return response.json().get("agents", [])


async def run_multi_turn_test(client: ConversationClient, agent: dict, mode_name: str) -> None:
    log(f"\n{'=' * 60}")
    log(f"Multi-Turn Test ({mode_name})")
    log(f"{'=' * 60}")
    log(f"Agent: {agent['name']} ({agent['agent_id']})")

    await client.connect()

    try:
        prompts = ["Say just 'OK'", "Say just 'YES'", "Say just 'HELLO'"]
        for i, prompt in enumerate(prompts, 1):
            log(f"\n--- Turn {i} ---")
            log(f'  Prompt: "{prompt}"')
            result = await client.send_message(prompt, agent_id=agent["agent_id"] if i == 1 else None)
            log(f'  Response: "{result.text[:100]}"' if result.text else "  Response: (empty)")
    finally:
        await client.close()

    log(f"\n{mode_name} test completed!")


async def main() -> None:
    parser = argparse.ArgumentParser(description="API Agent Selection & Multi-Turn Test")
    parser.add_argument("--mode", choices=["sse", "ws", "both"], default="both", help="Connection mode")
    args = parser.parse_args()

    log("=" * 60)
    log("API Agent Selection & Multi-Turn Test")
    log("=" * 60)

    agents = await get_agents()
    log(f"Found {len(agents)} agents")

    if not agents:
        log("ERROR: No agents available")
        return

    agent = agents[0]
    log(f"Selected: {agent['name']} ({agent['agent_id']})")

    if args.mode in ("sse", "both"):
        await run_multi_turn_test(SSEClient(), agent, "HTTP SSE")

    if args.mode in ("ws", "both"):
        await run_multi_turn_test(WebSocketClient(agent_id=agent["agent_id"]), agent, "WebSocket")


if __name__ == "__main__":
    asyncio.run(main())
