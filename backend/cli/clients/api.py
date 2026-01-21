"""HTTP/SSE client for API mode.

Provides a client that communicates with the FastAPI server via HTTP and SSE.
"""
import asyncio
import json
from typing import AsyncIterator, Optional

import httpx
from httpx_sse import aconnect_sse


class APIClient:
    """HTTP/SSE client for interacting with Claude Agent API."""

    def __init__(self, api_url: str = "http://localhost:7001"):
        """Initialize the API client.

        Args:
            api_url: Base URL of the API server.
        """
        self.api_url = api_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=300.0)
        self.session_id: Optional[str] = None
        self._resume_session_id: Optional[str] = None

    async def create_session(self, resume_session_id: Optional[str] = None) -> dict:
        """Create a new conversation session.

        Creates a session on the server and stores the session ID.
        For resumed sessions, uses the provided session_id directly.

        Args:
            resume_session_id: Optional session ID to resume.

        Returns:
            Dictionary with session information.
        """
        self._resume_session_id = resume_session_id

        if resume_session_id:
            # Resume existing session
            self.session_id = resume_session_id
            return {
                "session_id": resume_session_id,
                "status": "ready",
                "resumed": True
            }

        # Create new session via API
        endpoint = f"{self.api_url}/api/v1/sessions"
        try:
            response = await self.client.post(endpoint)
            response.raise_for_status()
            data = response.json()
            self.session_id = data.get("session_id")
            return {
                "session_id": self.session_id,
                "status": data.get("status", "connected"),
                "resumed": False
            }
        except Exception:
            self.session_id = None
            return {
                "session_id": "pending",
                "status": "ready",
                "resumed": False
            }

    async def send_message(self, content: str, session_id: Optional[str] = None) -> AsyncIterator[dict]:
        """Send a message and stream response events via SSE.

        All messages go through the stream endpoint.
        Session must be created first via create_session().

        Args:
            content: User message content.
            session_id: Optional session ID (uses stored session_id if not provided).

        Yields:
            Dictionary events from SSE stream.
        """
        sid = session_id or self.session_id

        if not sid:
            # No session - create one first
            await self.create_session()
            sid = self.session_id

        # All messages go through the stream endpoint
        endpoint = f"{self.api_url}/api/v1/conversations/{sid}/stream"
        payload = {"content": content}

        async with aconnect_sse(
            self.client,
            "POST",
            endpoint,
            json=payload
        ) as event_source:
            async for sse_event in event_source.aiter_sse():
                try:
                    # Parse SSE data
                    event_data = json.loads(sse_event.data) if sse_event.data else {}

                    # Convert SSE format to expected event format
                    if sse_event.event == "text_delta":
                        # SSE: event: text_delta, data: {"text": "..."}
                        # CLI expects: {"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "..."}}}
                        text = event_data.get("text", "")
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

                    elif sse_event.event == "tool_use":
                        yield {
                            "type": "tool_use",
                            "name": event_data.get("tool_name", ""),
                            "input": event_data.get("input", {})
                        }

                    elif sse_event.event == "tool_result":
                        # Tool result event with full content
                        tool_result = {
                            "type": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": event_data.get("tool_use_id", ""),
                                "content": event_data.get("content", ""),
                                "is_error": event_data.get("is_error", False)
                            }]
                        }
                        yield tool_result

                    elif sse_event.event == "session_id":
                        # Update stored session ID with real one from SDK
                        new_session_id = event_data.get("session_id")
                        if new_session_id:
                            self.session_id = new_session_id
                        yield {
                            "type": "init",
                            "session_id": new_session_id
                        }

                    elif sse_event.event == "done":
                        yield {
                            "type": "success",
                            "num_turns": event_data.get("turn_count", 0),
                            "total_cost_usd": event_data.get("total_cost_usd", 0.0)
                        }

                    elif sse_event.event == "error":
                        yield {
                            "type": "error",
                            "error": event_data.get("message", "Unknown error")
                        }

                    elif sse_event.event == "message":
                        # Generic message event - pass through
                        yield event_data

                except json.JSONDecodeError:
                    # Skip malformed events
                    continue
                except Exception:
                    # Log and continue
                    continue

    async def interrupt(self, session_id: Optional[str] = None) -> bool:
        """Interrupt the current task for a session.

        Args:
            session_id: Optional session ID (uses stored session_id if not provided).

        Returns:
            True if interrupt was successful.
        """
        sid = session_id or self.session_id
        if not sid:
            return False

        endpoint = f"{self.api_url}/api/v1/conversations/{sid}/interrupt"
        try:
            response = await self.client.post(endpoint)
            response.raise_for_status()
            return True
        except Exception:
            return False

    async def close_session(self, session_id: str):
        """Close a specific session (keeps in history).

        Args:
            session_id: Session ID to close.
        """
        endpoint = f"{self.api_url}/api/v1/sessions/{session_id}/close"
        try:
            response = await self.client.post(endpoint)
            response.raise_for_status()
        except Exception:
            pass  # Best effort

        if self.session_id == session_id:
            self.session_id = None

    async def resume_previous_session(self) -> Optional[dict]:
        """Resume the session right before the current one.

        Sessions are ordered newest first. This finds the current session's
        position and returns the one immediately after it (the previous session
        chronologically).

        Returns:
            Dictionary with session info or None if no previous session.
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

    async def disconnect(self):
        """Disconnect the HTTP client."""
        await self.client.aclose()

    async def list_sessions(self) -> list[dict]:
        """List all sessions ordered by recency (newest first).

        Returns:
            List of session dictionaries with session_id, first_message, and is_current flag.
        """
        endpoint = f"{self.api_url}/api/v1/sessions"
        try:
            response = await self.client.get(endpoint)
            response.raise_for_status()
            data = response.json()
            # Response is a list of SessionInfo objects
            sessions = []
            for session in data:
                session_id = session.get("session_id")
                sessions.append({
                    "session_id": session_id,
                    "first_message": session.get("first_message"),
                    "turn_count": session.get("turn_count", 0),
                    "created_at": session.get("created_at"),
                    "is_current": session_id == self.session_id
                })
            return sessions
        except Exception:
            return []

    async def list_skills(self) -> list[dict]:
        """List available skills.

        Returns:
            List of skill dictionaries.
        """
        endpoint = f"{self.api_url}/api/v1/config/skills"
        try:
            response = await self.client.get(endpoint)
            response.raise_for_status()
            data = response.json()
            # Convert from API format to expected format
            return data.get("skills", [])
        except Exception:
            return []

    async def list_agents(self) -> list[dict]:
        """List available top-level agents (for agent_id selection).

        Returns:
            List of agent dictionaries with agent_id, name, type, etc.
        """
        endpoint = f"{self.api_url}/api/v1/config/agents"
        try:
            response = await self.client.get(endpoint)
            response.raise_for_status()
            data = response.json()
            return data.get("agents", [])
        except Exception:
            return []

    async def list_subagents(self) -> list[dict]:
        """List available subagents (for delegation within conversations).

        Returns:
            List of subagent dictionaries with name and focus.
        """
        endpoint = f"{self.api_url}/api/v1/config/subagents"
        try:
            response = await self.client.get(endpoint)
            response.raise_for_status()
            data = response.json()
            return data.get("subagents", [])
        except Exception:
            return []

    def update_turn_count(self, turn_count: int) -> None:
        """Update turn count (stored locally, API tracks server-side).

        Args:
            turn_count: Current turn count to save.
        """
        # API mode tracks turn count server-side, this is a no-op
        # but maintains interface compatibility
        pass
