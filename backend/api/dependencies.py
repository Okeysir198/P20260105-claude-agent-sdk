"""FastAPI dependencies for API routes.

Provides dependency injection functions for FastAPI routes to access
shared services and configuration.
"""
from typing import Annotated

from fastapi import Depends

from api.services.session_manager import get_session_manager, SessionManager


async def _get_session_manager_dependency() -> SessionManager:
    """FastAPI dependency that returns the SessionManager singleton.

    This is an internal wrapper function used by FastAPI's dependency injection.
    Use the `SessionManagerDep` type alias in route signatures.

    Returns:
        The global SessionManager instance.

    Example:
        ```python
        from fastapi import APIRouter, Depends
        from api.dependencies import SessionManagerDep
        from api.models import SessionListResponse

        router = APIRouter()

        @router.get("/sessions", response_model=SessionListResponse)
        async def list_sessions(manager: SessionManagerDep):
            sessions = manager.list_sessions()
            return SessionListResponse(sessions=sessions)
        ```
    """
    return get_session_manager()


# Type alias for use in route signatures
# Use this like: async def my_route(manager: SessionManagerDep)
SessionManagerDep = Annotated[SessionManager, Depends(_get_session_manager_dependency)]
