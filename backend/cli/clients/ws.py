"""WebSocket client for CLI chat.

Provides a persistent WebSocket connection for lower latency multi-turn conversations.
"""
import json
from typing import AsyncIterator, Optional

import httpx
import websockets
from websockets.exceptions import ConnectionClosed

from cli.clients import find_previous_session
from cli.clients.api import APIClient
from cli.clients.config import ClientConfig, get_default_config
from cli.clients.event_normalizer import (
    to_stream_event,
    to_init_event,
    to_success_event,
    to_error_event,
    to_info_event,
    to_tool_use_event,
    to_ask_user_event,
)


class WSClient:
    """WebSocket client for interacting with Claude Agent API.

    Uses WebSocket for streaming communication but delegates read-only
    operations (list_agents, list_sessions, etc.) to an internal APIClient.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        agent_id: Optional[str] = None,
        api_key: Optional[str] = None,
        config: Optional[ClientConfig] = None,
    ):
        """Initialize the WebSocket client.

        Args:
            api_url: Base URL of the API server. Overrides config.api_url if provided.
            agent_id: Optional agent ID to use for the connection.
            api_key: Optional API key for authentication. Overrides config.api_key if provided.
            config: Optional ClientConfig for all settings. Defaults to environment-based config.
        """
        self._config = config or get_default_config()

        # Override config with explicit arguments
        if api_url:
            self._config.api_url = api_url
        if api_key:
            self._config.api_key = api_key

        self.agent_id = agent_id
        self.session_id: Optional[str] = None
        self._ws = None
        self._connected = False
        self._api_client: Optional[APIClient] = None
        self._jwt_token: Optional[str] = None

    def _get_api_client(self) -> APIClient:
        """Get or create the internal API client for read operations."""
        if self._api_client is None:
            self._api_client = APIClient(
                api_url=self._config.http_url,
                api_key=self._config.api_key,
            )
        return self._api_client

    async def _get_jwt_token(self) -> str:
        """Get JWT token via user login.

        Logs in with username/password from config to get a user_identity
        token required for WebSocket auth. Prompts for password if not set.

        Returns:
            JWT access token with user identity claims.

        Raises:
            RuntimeError: If login fails.
        """
        if self._jwt_token:
            return self._jwt_token

        # Prompt for password if not set in environment
        password = self._config.password
        if not password:
            import getpass
            password = getpass.getpass(f"Password for {self._config.username}: ")
            if not password:
                raise RuntimeError("Password is required for authentication")

        headers = {"Content-Type": "application/json"}
        if self._config.api_key:
            headers["X-API-Key"] = self._config.api_key

        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            # Login to get user_identity token
            response = await client.post(
                f"{self._config.http_url}/api/v1/auth/login",
                json={
                    "username": self._config.username,
                    "password": password,
                }
            )

            if response.status_code != 200:
                raise RuntimeError(f"Login failed: {response.text}")

            data = response.json()
            if not data.get("success"):
                raise RuntimeError(f"Login failed: {data.get('error', 'Unknown error')}")

            self._jwt_token = data.get("token")
            if not self._jwt_token:
                raise RuntimeError("Login response missing token")

            return self._jwt_token

    def _build_ws_url(self, resume_session_id: Optional[str] = None) -> str:
        """Build WebSocket URL with query parameters.

        Args:
            resume_session_id: Optional session ID to resume.

        Returns:
            Complete WebSocket URL with query parameters.
        """
        url = f"{self._config.ws_url}{self._config.ws_chat_endpoint}"
        params = []

        if self.agent_id:
            params.append(f"agent_id={self.agent_id}")
        if resume_session_id:
            params.append(f"session_id={resume_session_id}")
        if self._jwt_token:
            params.append(f"token={self._jwt_token}")

        if params:
            url += "?" + "&".join(params)

        return url

    async def create_session(self, resume_session_id: Optional[str] = None) -> dict:
        """Create a new WebSocket session or resume an existing one.

        Args:
            resume_session_id: Optional session ID to resume.

        Returns:
            Dictionary with session information.
        """
        # Close existing connection if any
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
            self._connected = False

        # Get JWT token via user login (required for WebSocket auth)
        await self._get_jwt_token()

        url = self._build_ws_url(resume_session_id)

        try:
            self._ws = await websockets.connect(
                url,
                ping_interval=self._config.ws_ping_interval,
                ping_timeout=self._config.ws_ping_timeout,
                close_timeout=self._config.ws_close_timeout,
            )
            self._connected = True

            # Wait for ready signal
            ready_msg = await self._ws.recv()
            data = json.loads(ready_msg)

            if data.get("type") == "error":
                self._connected = False
                await self._ws.close()
                raise RuntimeError(data.get("error", "Unknown error"))

            if data.get("type") != "ready":
                raise RuntimeError(f"Unexpected ready signal: {data}")

            resumed = data.get("resumed", False)
            session_id = data.get("session_id") if resumed else None
            turn_count = data.get("turn_count", 0) if resumed else 0

            if resumed and session_id:
                self.session_id = session_id

            return {
                "session_id": session_id or "ws-connected",
                "status": "ready",
                "resumed": resumed,
                "turn_count": turn_count,
            }
        except Exception as e:
            self._connected = False
            raise RuntimeError(f"Failed to connect WebSocket: {e}")

    async def send_message(self, content: str, session_id: Optional[str] = None) -> AsyncIterator[dict]:
        """Send a message and stream response events via WebSocket.

        Args:
            content: User message content.
            session_id: Ignored in WebSocket mode (connection maintains state).

        Yields:
            Dictionary events from WebSocket stream.
        """
        max_retries = 1
        retry_count = 0

        while retry_count <= max_retries:
            # Auto-reconnect if disconnected but we have a session_id
            if (not self._ws or not self._connected) and self.session_id:
                try:
                    yield to_info_event(f"Reconnecting to session {self.session_id}...")
                    await self.create_session(resume_session_id=self.session_id)
                    yield to_info_event("Reconnected successfully")
                except Exception as e:
                    yield to_error_event(f"Failed to reconnect: {e}")
                    return

            if not self._ws or not self._connected:
                raise RuntimeError("WebSocket not connected. Call create_session() first.")

            # Send message
            try:
                await self._ws.send(json.dumps({"content": content}))
            except ConnectionClosed:
                self._connected = False
                retry_count += 1
                if retry_count <= max_retries and self.session_id:
                    continue
                yield to_error_event("WebSocket connection closed while sending")
                return

            # Receive responses
            try:
                async for event in self._receive_events():
                    yield event
                    if event.get("type") in ("success", "error"):
                        return
            except ConnectionClosed:
                self._connected = False
                retry_count += 1
                if retry_count <= max_retries and self.session_id:
                    yield to_info_event("Connection lost, retrying...")
                    continue
                yield to_error_event("WebSocket connection closed")
                return

    async def _receive_events(self) -> AsyncIterator[dict]:
        """Receive and convert WebSocket events to CLI format.

        Yields:
            Dictionary events in CLI format.
        """
        while True:
            msg = await self._ws.recv()
            data = json.loads(msg)
            msg_type = data.get("type")

            if msg_type == "session_id":
                self.session_id = data["session_id"]
                yield to_init_event(self.session_id)

            elif msg_type == "text_delta":
                text = data.get("text", "")
                if text:
                    yield to_stream_event(text)

            elif msg_type == "tool_use":
                yield to_tool_use_event(
                    name=data.get("name", ""),
                    input_data=data.get("input", {}),
                )

            elif msg_type == "done":
                yield to_success_event(
                    num_turns=data.get("turn_count", 0),
                    total_cost_usd=data.get("total_cost_usd", 0.0),
                )
                return

            elif msg_type == "error":
                yield to_error_event(data.get("error", "Unknown error"))
                return

            elif msg_type == "ask_user_question":
                yield to_ask_user_event(
                    question_id=data.get("question_id"),
                    questions=data.get("questions", []),
                    timeout=data.get("timeout", 60),
                )

            elif msg_type == "ready":
                # Ignore ready signals during conversation
                pass

    async def send_answer(self, question_id: str, answers: dict) -> None:
        """Send user answers for an AskUserQuestion prompt.

        Args:
            question_id: The question ID from the ask_user_question event.
            answers: Dictionary mapping question text to user's answer.
        """
        if not self._ws or not self._connected:
            raise RuntimeError("WebSocket not connected")

        await self._ws.send(json.dumps({
            "type": "user_answer",
            "question_id": question_id,
            "answers": answers,
        }))

    async def interrupt(self, session_id: Optional[str] = None) -> bool:
        """Interrupt the current task.

        Note: WebSocket mode doesn't support interrupt via separate endpoint.

        Returns:
            False (not supported in WebSocket mode).
        """
        return False

    async def close_session(self, session_id: str) -> None:
        """Close a specific session.

        In WebSocket mode, this is a no-op as sessions are tied to connections.
        """
        pass

    async def resume_previous_session(self) -> Optional[dict]:
        """Resume the session right before the current one.

        Returns:
            Session info dict if resumed, None if no previous session exists.
        """
        try:
            sessions = await self.list_sessions()
            prev_id = await find_previous_session(sessions, self.session_id)
            if prev_id:
                return await self.create_session(resume_session_id=prev_id)
            return None
        except Exception:
            return None

    async def disconnect(self) -> None:
        """Disconnect the WebSocket connection and cleanup resources."""
        if self._ws:
            await self._ws.close()
            self._ws = None
        self._connected = False

        if self._api_client:
            await self._api_client.disconnect()
            self._api_client = None

    async def list_sessions(self) -> list[dict]:
        """List all sessions."""
        return await self._get_api_client().list_sessions()

    async def list_skills(self) -> list[dict]:
        """List available skills."""
        return await self._get_api_client().list_skills()

    async def list_agents(self) -> list[dict]:
        """List available agents."""
        return await self._get_api_client().list_agents()

    async def list_subagents(self) -> list[dict]:
        """List available subagents."""
        return await self._get_api_client().list_subagents()

    def update_turn_count(self, turn_count: int) -> None:
        """Update turn count (no-op for WebSocket client)."""
        pass

    async def switch_agent(self, new_agent_id: str) -> dict:
        """Switch to a different agent by creating a new session.

        Args:
            new_agent_id: The agent ID to switch to.

        Returns:
            Session info dict for the new session.
        """
        self.agent_id = new_agent_id
        self.session_id = None
        return await self.create_session()
