"""FastAPI dependencies for authentication and session management."""
from typing import Annotated

from fastapi import Depends

from api.dependencies.auth import (
    get_current_user,
    get_current_user_optional,
    get_current_user_ws,
)
from api.services.session_manager import get_session_manager, SessionManager


async def _get_session_manager_dependency() -> SessionManager:
    """Return the SessionManager singleton for dependency injection."""
    return get_session_manager()


SessionManagerDep = Annotated[SessionManager, Depends(_get_session_manager_dependency)]


__all__ = [
    "get_current_user",
    "get_current_user_optional",
    "get_current_user_ws",
    "SessionManagerDep",
]
