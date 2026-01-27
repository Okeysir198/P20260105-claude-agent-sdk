"""FastAPI dependencies for API routes.

Provides dependency injection functions for authentication and session management.
"""
from typing import Annotated

from fastapi import Depends

from api.dependencies.auth import (
    get_current_user,
    get_current_user_optional,
    get_current_user_ws,
)
from api.services.session_manager import get_session_manager, SessionManager


async def _get_session_manager_dependency() -> SessionManager:
    """FastAPI dependency that returns the SessionManager singleton.

    This is an internal wrapper function used by FastAPI's dependency injection.
    Use the `SessionManagerDep` type alias in route signatures.

    Returns:
        The global SessionManager instance.
    """
    return get_session_manager()


# Type alias for use in route signatures
# Use this like: async def my_route(manager: SessionManagerDep)
SessionManagerDep = Annotated[SessionManager, Depends(_get_session_manager_dependency)]


__all__ = [
    "get_current_user",
    "get_current_user_optional",
    "get_current_user_ws",
    "SessionManagerDep",
]
