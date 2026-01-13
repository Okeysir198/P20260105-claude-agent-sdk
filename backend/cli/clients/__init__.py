"""CLI client modules.

Contains the DirectClient and APIClient for SDK and HTTP/SSE interaction.
"""
from typing import Protocol, AsyncIterator, Optional, runtime_checkable


@runtime_checkable
class BaseClient(Protocol):
    """Protocol defining the common client interface.

    Both DirectClient and APIClient must implement these methods
    with consistent signatures (all async).
    """
    session_id: Optional[str]

    async def create_session(self, resume_session_id: Optional[str] = None) -> dict:
        """Create or resume a conversation session."""
        ...

    async def send_message(self, content: str, session_id: Optional[str] = None) -> AsyncIterator[dict]:
        """Send a message and stream response events."""
        ...

    async def interrupt(self, session_id: Optional[str] = None) -> bool:
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

    def update_turn_count(self, turn_count: int) -> None:
        """Update turn count (may be no-op for some clients)."""
        ...


from .direct import DirectClient
from .api import APIClient

__all__ = [
    'BaseClient',
    'DirectClient',
    'APIClient',
]
