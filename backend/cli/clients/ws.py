"""WebSocket client for CLI chat.

Provides a persistent WebSocket connection for lower latency multi-turn conversations.
"""
import json
from typing import AsyncIterator, Optional

import websockets
from websockets.exceptions import ConnectionClosed

from cli.clients.api import APIClient


class WSClient:
    """WebSocket client for interacting with Claude Agent API.

    Uses WebSocket for streaming communication but delegates read-only
    operations (list_agents, list_sessions, etc.) to an internal APIClient.
    """

    def __init__(self, api_url: str = "http://localhost:7001", agent_id: Optional[str] = None):
        """Initialize the WebSocket client.

        Args:
            api_url: Base URL of the API server (http:// will be converted to ws://).
            agent_id: Optional agent ID to use for the connection.
        """
        # Store the HTTP API URL for the internal API client
        self._http_api_url = api_url.rstrip('/')

        # Convert http(s) to ws(s)
        ws_url = api_url.replace("https://", "wss://").replace("http://", "ws://")
        self.ws_url = ws_url.rstrip('/')
        self.agent_id = agent_id
        self.session_id: Optional[str] = None
        self._ws = None
        self._connected = False

        # Internal API client for read operations (list_*, etc.)
        self._api_client: Optional[APIClient] = None

    def _get_api_client(self) -> APIClient:
        """Get or create the internal API client for read operations.

        Returns:
            APIClient instance for making HTTP requests.
        """
        if self._api_client is None:
            self._api_client = APIClient(self._http_api_url)
        return self._api_client

    async def create_session(self, resume_session_id: Optional[str] = None) -> dict:
        """Create a new WebSocket session or resume an existing one.

        Establishes the WebSocket connection and waits for ready signal.
        If resume_session_id is provided, connects with the session_id parameter
        to resume the session on the backend.

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

        # Build WebSocket URL with query parameters
        url = f"{self.ws_url}/api/v1/ws/chat"
        params = []
        if self.agent_id:
            params.append(f"agent_id={self.agent_id}")
        if resume_session_id:
            params.append(f"session_id={resume_session_id}")
        if params:
            url += "?" + "&".join(params)

        try:
            self._ws = await websockets.connect(url)
            self._connected = True

            # Wait for ready signal
            ready_msg = await self._ws.recv()
            data = json.loads(ready_msg)

            if data.get("type") == "error":
                # Session not found or other error
                self._connected = False
                await self._ws.close()
                raise RuntimeError(data.get("error", "Unknown error"))

            if data.get("type") != "ready":
                raise RuntimeError(f"Unexpected ready signal: {data}")

            # Check if this is a resumed session
            resumed = data.get("resumed", False)
            session_id = data.get("session_id") if resumed else None
            turn_count = data.get("turn_count", 0) if resumed else 0

            if resumed and session_id:
                self.session_id = session_id

            return {
                "session_id": session_id or "ws-connected",
                "status": "ready",
                "resumed": resumed,
                "turn_count": turn_count
            }
        except Exception as e:
            self._connected = False
            raise RuntimeError(f"Failed to connect WebSocket: {e}")

    async def send_message(self, content: str, session_id: Optional[str] = None) -> AsyncIterator[dict]:
        """Send a message and stream response events via WebSocket.

        If the connection is lost but we have a session_id, automatically
        attempts to reconnect before sending the message. Also handles
        reconnection if connection drops mid-stream.

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
                    yield {
                        "type": "info",
                        "message": f"Reconnecting to session {self.session_id}..."
                    }
                    await self.create_session(resume_session_id=self.session_id)
                    yield {
                        "type": "info",
                        "message": "Reconnected successfully"
                    }
                except Exception as e:
                    yield {
                        "type": "error",
                        "error": f"Failed to reconnect: {e}"
                    }
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
                    continue  # Try to reconnect and resend
                yield {
                    "type": "error",
                    "error": "WebSocket connection closed while sending"
                }
                return

            # Receive responses
            try:
                while True:
                    msg = await self._ws.recv()
                    data = json.loads(msg)
                    msg_type = data.get("type")

                    if msg_type == "session_id":
                        # Got SDK session ID
                        self.session_id = data["session_id"]
                        yield {
                            "type": "init",
                            "session_id": self.session_id
                        }

                    elif msg_type == "text_delta":
                        # Streaming text
                        text = data.get("text", "")
                        if text:
                            yield {
                                "type": "stream_event",
                                "event": {
                                    "type": "content_block_delta",
                                    "delta": {
                                        "type": "text_delta",
                                        "text": text
                                    }
                                }
                            }

                    elif msg_type == "tool_use":
                        yield {
                            "type": "tool_use",
                            "name": data.get("name", ""),
                            "input": data.get("input", {})
                        }

                    elif msg_type == "done":
                        yield {
                            "type": "success",
                            "num_turns": data.get("turn_count", 0),
                            "total_cost_usd": data.get("total_cost_usd", 0.0)
                        }
                        return  # Success, exit the retry loop

                    elif msg_type == "error":
                        yield {
                            "type": "error",
                            "error": data.get("error", "Unknown error")
                        }
                        return  # Error from server, don't retry

                    elif msg_type == "ready":
                        # Ignore ready signals during conversation
                        pass

            except ConnectionClosed:
                self._connected = False
                retry_count += 1
                if retry_count <= max_retries and self.session_id:
                    yield {
                        "type": "info",
                        "message": "Connection lost, retrying..."
                    }
                    continue  # Try to reconnect and resend
                yield {
                    "type": "error",
                    "error": "WebSocket connection closed"
                }
                return

    async def interrupt(self, session_id: Optional[str] = None) -> bool:
        """Interrupt the current task.

        Note: WebSocket mode doesn't support interrupt via separate endpoint.

        Args:
            session_id: Ignored in WebSocket mode.

        Returns:
            False (not supported in WebSocket mode).
        """
        # WebSocket mode doesn't have a separate interrupt mechanism
        return False

    async def close_session(self, session_id: str) -> None:
        """Close a specific session.

        In WebSocket mode, this is a no-op as sessions are tied to connections.

        Args:
            session_id: Session ID to close (ignored).
        """
        pass

    async def resume_previous_session(self) -> Optional[dict]:
        """Resume the session right before the current one.

        Sessions are ordered newest first. This finds the current session's
        position and returns the one immediately after it (the previous session
        chronologically).

        Returns:
            Session info dict if resumed, None if no previous session exists.
        """
        try:
            sessions = await self.list_sessions()
            if not sessions:
                return None

            # Find current session's index
            current_index = -1
            for i, session in enumerate(sessions):
                if session.get("session_id") == self.session_id:
                    current_index = i
                    break

            # If current session found, get the one right after it (previous chronologically)
            if current_index >= 0 and current_index + 1 < len(sessions):
                prev_session = sessions[current_index + 1]
                return await self.create_session(resume_session_id=prev_session["session_id"])

            # If current session not found or is oldest, return the most recent one
            # (useful when starting fresh or current session hasn't been saved yet)
            if current_index == -1 and sessions:
                return await self.create_session(resume_session_id=sessions[0]["session_id"])

            return None
        except Exception:
            return None

    async def disconnect(self) -> None:
        """Disconnect the WebSocket connection and cleanup resources."""
        if self._ws:
            await self._ws.close()
            self._ws = None
        self._connected = False

        # Cleanup internal API client if it was created
        if self._api_client:
            await self._api_client.disconnect()
            self._api_client = None

    async def list_sessions(self) -> list[dict]:
        """List all sessions.

        Delegates to internal HTTP API client for session listing.

        Returns:
            List of session dictionaries with session_id and is_current flag.
        """
        return await self._get_api_client().list_sessions()

    async def list_skills(self) -> list[dict]:
        """List available skills.

        Delegates to internal HTTP API client for skill listing.

        Returns:
            List of skill dictionaries.
        """
        return await self._get_api_client().list_skills()

    async def list_agents(self) -> list[dict]:
        """List available agents.

        Delegates to internal HTTP API client for agent listing.

        Returns:
            List of agent dictionaries with agent_id, name, type, etc.
        """
        return await self._get_api_client().list_agents()

    async def list_subagents(self) -> list[dict]:
        """List available subagents.

        Delegates to internal HTTP API client for subagent listing.

        Returns:
            List of subagent dictionaries with name and focus.
        """
        return await self._get_api_client().list_subagents()

    def update_turn_count(self, turn_count: int) -> None:
        """Update turn count (no-op for WebSocket client).

        Args:
            turn_count: Current turn count.
        """
        pass
