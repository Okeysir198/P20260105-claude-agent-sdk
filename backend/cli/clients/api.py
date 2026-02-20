"""HTTP/SSE client for API mode.

Provides a client that communicates with the FastAPI server via HTTP and SSE.
"""
import json
from collections.abc import AsyncIterator

import httpx
from httpx_sse import aconnect_sse

from cli.clients.auth import perform_login
from cli.clients.config import ClientConfig, get_default_config
from cli.clients.event_normalizer import (
    to_cancelled_event,
    to_compact_completed_event,
    to_compact_started_event,
    to_error_event,
    to_init_event,
    to_stream_event,
    to_success_event,
    to_thinking_event,
    to_assistant_text_event,
    to_tool_use_event,
)


class APIClient:
    """HTTP/SSE client for interacting with Claude Agent API."""

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        config: ClientConfig | None = None,
        agent_id: str | None = None,
        jwt_token: str | None = None,
    ):
        """Initialize the API client.

        Args:
            api_url: Base URL of the API server. Overrides config.api_url if provided.
            api_key: Optional API key for authentication. Overrides config.api_key if provided.
            config: Optional ClientConfig for all settings. Defaults to environment-based config.
            agent_id: Optional agent ID to use for conversations.
            jwt_token: Optional JWT token for user authentication. If not provided, will login lazily.
        """
        self._config = config or get_default_config()

        # Override config with explicit arguments
        if api_url:
            self._config.api_url = api_url
        if api_key:
            self._config.api_key = api_key

        headers = {}
        if self._config.api_key:
            headers["X-API-Key"] = self._config.api_key

        self._jwt_token = jwt_token
        if jwt_token:
            headers["X-User-Token"] = jwt_token

        self.client = httpx.AsyncClient(timeout=self._config.http_timeout, headers=headers)
        self.session_id: str | None = None
        self._resume_session_id: str | None = None
        self._agent_id: str | None = agent_id

    async def _login(self) -> None:
        """Login to get a JWT token for user authentication.

        Prompts for password if not set in config. Stores the token
        and adds the X-User-Token header to the HTTP client.

        Raises:
            RuntimeError: If login fails.
        """
        self._jwt_token = await perform_login(
            http_url=self._config.http_url,
            username=self._config.username,
            password=self._config.password,
            api_key=self._config.api_key,
        )
        self.client.headers["X-User-Token"] = self._jwt_token

    async def _ensure_authenticated(self) -> None:
        """Ensure the client has a valid JWT token, logging in if needed."""
        if self._jwt_token is None:
            await self._login()

    async def create_session(self, resume_session_id: str | None = None) -> dict:
        """Create a new conversation session.

        Args:
            resume_session_id: Optional session ID to resume.

        Returns:
            Dictionary with session information.
        """
        self._resume_session_id = resume_session_id

        if resume_session_id:
            self.session_id = resume_session_id
            return {
                "session_id": resume_session_id,
                "status": "ready",
                "resumed": True,
            }

        # SSE mode doesn't pre-create sessions; session_id comes from first message
        # Return pending status; actual session_id will be set when send_message is called
        self.session_id = None
        return {
            "session_id": "pending",
            "status": "ready",
            "resumed": False,
        }

    async def send_message(self, content: str, session_id: str | None = None) -> AsyncIterator[dict]:
        """Send a message and stream response events via SSE.

        Args:
            content: User message content.
            session_id: Optional session ID (uses stored session_id if not provided).

        Yields:
            Dictionary events from SSE stream.
        """
        await self._ensure_authenticated()
        sid = session_id or self.session_id

        # Determine endpoint - new conversation vs follow-up
        if sid:
            # Follow-up message to existing session
            endpoint = f"{self._config.http_url}{self._config.conversations_endpoint}/{sid}/stream"
        else:
            # New conversation - use conversations endpoint
            endpoint = f"{self._config.http_url}{self._config.conversations_endpoint}"

        payload = {"content": content}
        if self._agent_id:
            payload["agent_id"] = self._agent_id
        if sid:
            payload["session_id"] = sid

        async with aconnect_sse(
            self.client,
            "POST",
            endpoint,
            json=payload,
        ) as event_source:
            async for sse_event in event_source.aiter_sse():
                event = self._convert_sse_event(sse_event)
                if event:
                    # Update session_id if we get an init event
                    if event.get("type") == "init" and "session_id" in event:
                        self.session_id = event["session_id"]
                    yield event

    def _convert_sse_event(self, sse_event) -> dict | None:
        """Convert SSE event to CLI format.

        Args:
            sse_event: The SSE event object.

        Returns:
            Converted event dictionary or None if event should be skipped.
        """
        try:
            event_data = json.loads(sse_event.data) if sse_event.data else {}
        except json.JSONDecodeError:
            return None

        if sse_event.event == "text_delta":
            text = event_data.get("text", "")
            if text:
                return to_stream_event(text)
            return None

        if sse_event.event == "tool_use":
            return to_tool_use_event(
                name=event_data.get("tool_name", ""),
                input_data=event_data.get("input", {}),
            )

        if sse_event.event == "tool_result":
            return {
                "type": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": event_data.get("tool_use_id", ""),
                    "content": event_data.get("content", ""),
                    "is_error": event_data.get("is_error", False),
                }],
            }

        if sse_event.event == "session_id":
            new_session_id = event_data.get("session_id")
            if new_session_id:
                return to_init_event(new_session_id)
            return None

        if sse_event.event == "done":
            return to_success_event(
                num_turns=event_data.get("turn_count", 0),
                total_cost_usd=event_data.get("total_cost_usd", 0.0),
            )

        if sse_event.event == "error":
            return to_error_event(event_data.get("message", "Unknown error"))

        if sse_event.event == "message":
            return event_data

        if sse_event.event == "cancelled":
            return to_cancelled_event()

        if sse_event.event == "compact_started":
            return to_compact_started_event()

        if sse_event.event == "compact_completed":
            return to_compact_completed_event(
                summary=event_data.get("summary", "")
            )

        if sse_event.event == "thinking":
            text = event_data.get("text", "")
            if text:
                return to_thinking_event(text)
            return None

        if sse_event.event == "assistant_text":
            text = event_data.get("text", "")
            if text:
                return to_assistant_text_event(text)
            return None

        return None

    async def interrupt(self, session_id: str | None = None) -> bool:
        """Interrupt the current task for a session.

        Args:
            session_id: Optional session ID (uses stored session_id if not provided).

        Returns:
            True if interrupt was successful.
        """
        await self._ensure_authenticated()
        sid = session_id or self.session_id
        if not sid:
            return False

        endpoint = f"{self._config.http_url}{self._config.conversations_endpoint}/{sid}/interrupt"
        try:
            response = await self.client.post(endpoint)
            response.raise_for_status()
            return True
        except Exception:
            return False

    async def close_session(self, session_id: str) -> None:
        """Close a specific session (keeps in history).

        Args:
            session_id: Session ID to close.
        """
        await self._ensure_authenticated()
        endpoint = f"{self._config.http_url}{self._config.sessions_endpoint}/{session_id}/close"
        try:
            response = await self.client.post(endpoint)
            response.raise_for_status()
        except Exception:
            pass

        if self.session_id == session_id:
            self.session_id = None

    async def resume_previous_session(self) -> dict | None:
        """Resume the session right before the current one.

        Returns:
            Dictionary with session info or None if no previous session.
        """
        await self._ensure_authenticated()
        try:
            from cli.clients import find_previous_session
            sessions = await self.list_sessions()
            prev_id = await find_previous_session(sessions, self.session_id)
            if prev_id:
                return await self.create_session(resume_session_id=prev_id)
            return None
        except Exception:
            return None

    async def disconnect(self) -> None:
        """Disconnect the HTTP client."""
        await self.client.aclose()

    async def _fetch_list(self, endpoint: str, response_key: str) -> list[dict]:
        """Fetch a list of items from an API endpoint.

        Args:
            endpoint: Full URL to fetch from.
            response_key: Key to extract from the JSON response.

        Returns:
            List of item dictionaries, or empty list on failure.
        """
        await self._ensure_authenticated()
        try:
            response = await self.client.get(endpoint)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
            return data.get(response_key, [])
        except Exception:
            return []

    async def list_sessions(self) -> list[dict]:
        """List all sessions ordered by recency (newest first)."""
        endpoint = f"{self._config.http_url}{self._config.sessions_endpoint}"
        sessions = await self._fetch_list(endpoint, "sessions")
        return [
            {
                "session_id": session.get("session_id"),
                "first_message": session.get("first_message"),
                "turn_count": session.get("turn_count", 0),
                "created_at": session.get("created_at"),
                "is_current": session.get("session_id") == self.session_id,
            }
            for session in sessions
        ]

    async def search_sessions(self, query: str, max_results: int = 20) -> list[dict]:
        """Search sessions by content."""
        await self._ensure_authenticated()
        endpoint = f"{self._config.http_url}{self._config.sessions_endpoint}/search"
        try:
            response = await self.client.get(endpoint, params={"query": query, "max_results": max_results})
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except Exception:
            return []

    async def list_skills(self) -> list[dict]:
        """List available skills."""
        endpoint = f"{self._config.http_url}{self._config.config_endpoint}/skills"
        return await self._fetch_list(endpoint, "skills")

    async def list_agents(self) -> list[dict]:
        """List available top-level agents."""
        endpoint = f"{self._config.http_url}{self._config.config_endpoint}/agents"
        return await self._fetch_list(endpoint, "agents")

    async def list_subagents(self) -> list[dict]:
        """List available subagents."""
        endpoint = f"{self._config.http_url}{self._config.config_endpoint}/subagents"
        return await self._fetch_list(endpoint, "subagents")

    def update_turn_count(self, turn_count: int) -> None:
        """Update turn count (API tracks server-side, this is a no-op)."""
        pass
