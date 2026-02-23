"""CLI client modules."""
from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from .config import ClientConfig, get_default_config


@runtime_checkable
class BaseClient(Protocol):
    """Protocol defining the common client interface."""

    session_id: str | None

    async def create_session(self, resume_session_id: str | None = None) -> dict: ...
    async def send_message(self, content: str, session_id: str | None = None) -> AsyncIterator[dict]: ...
    async def interrupt(self, session_id: str | None = None) -> bool: ...
    async def disconnect(self) -> None: ...
    async def close_session(self, session_id: str) -> None: ...
    async def list_skills(self) -> list[dict]: ...
    async def list_agents(self) -> list[dict]: ...
    async def list_subagents(self) -> list[dict]: ...
    async def list_sessions(self) -> list[dict]: ...
    async def resume_previous_session(self) -> dict | None: ...
    def update_turn_count(self, turn_count: int) -> None: ...


async def find_previous_session(
    sessions: list[dict],
    current_session_id: str | None,
) -> str | None:
    """Find the previous session ID from a list of sessions.

    Returns the session after the current one in the list, or the first
    session if the current one is not found.
    """
    if not sessions:
        return None

    current_index = next(
        (i for i, s in enumerate(sessions) if s.get("session_id") == current_session_id),
        -1,
    )

    if current_index >= 0 and current_index + 1 < len(sessions):
        return sessions[current_index + 1].get("session_id")

    if current_index == -1:
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
