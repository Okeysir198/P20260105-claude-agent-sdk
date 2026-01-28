"""CLI client modules.

Contains the DirectClient, APIClient, and WSClient for SDK and HTTP/SSE interaction.
"""
from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from .config import ClientConfig, get_default_config


@runtime_checkable
class BaseClient(Protocol):
    """Protocol defining the common client interface.

    Both DirectClient and APIClient must implement these methods
    with consistent signatures (all async).
    """
    session_id: str | None

    async def create_session(self, resume_session_id: str | None = None) -> dict:
        """Create or resume a conversation session."""
        ...

    async def send_message(self, content: str, session_id: str | None = None) -> AsyncIterator[dict]:
        """Send a message and stream response events."""
        ...

    async def interrupt(self, session_id: str | None = None) -> bool:
        """Interrupt the current task."""
        ...

    async def disconnect(self) -> None:
        """Disconnect and cleanup."""
        ...

    async def close_session(self, session_id: str) -> None:
        """Close a specific session."""
        ...

    async def list_skills(self) -> list[dict]:
        """List available skills."""
        ...

    async def list_agents(self) -> list[dict]:
        """List available top-level agents (for agent_id selection)."""
        ...

    async def list_subagents(self) -> list[dict]:
        """List available subagents (for delegation within conversations)."""
        ...

    async def list_sessions(self) -> list[dict]:
        """List session history."""
        ...

    async def resume_previous_session(self) -> dict | None:
        """Resume the session right before the current one."""
        ...

    def update_turn_count(self, turn_count: int) -> None:
        """Update turn count (may be no-op for some clients)."""
        ...


async def find_previous_session(
    sessions: list[dict],
    current_session_id: str | None,
) -> str | None:
    """Find the previous session ID from a list of sessions.

    Args:
        sessions: List of session dictionaries with 'session_id' key.
        current_session_id: The current session ID.

    Returns:
        The previous session ID, or None if not found.
    """
    if not sessions:
        return None

    current_index = -1
    for i, session in enumerate(sessions):
        if session.get("session_id") == current_session_id:
            current_index = i
            break

    if current_index >= 0 and current_index + 1 < len(sessions):
        return sessions[current_index + 1].get("session_id")

    if current_index == -1 and sessions:
        return sessions[0].get("session_id")

    return None


from .direct import DirectClient
from .api import APIClient
from .ws import WSClient

__all__ = [
    "BaseClient",
    "ClientConfig",
    "get_default_config",
    "find_previous_session",
    "DirectClient",
    "APIClient",
    "WSClient",
]
