"""Context variables for media tools with environment variable fallback."""
import contextvars
import logging
import os

logger = logging.getLogger(__name__)


class _ContextValue:
    """Thread-safe context variable with environment variable fallback."""

    def __init__(self, name: str, env_var: str, label: str) -> None:
        self._var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
            name, default=None
        )
        self._env_var = env_var
        self._label = label

    def set(self, value: str) -> contextvars.Token[str | None]:
        return self._var.set(value)

    def reset(self, token: contextvars.Token[str | None]) -> None:
        self._var.reset(token)

    def get(self) -> str:
        value = self._var.get()
        if value:
            return value
        value = os.environ.get(self._env_var)
        if value:
            logger.debug(f"Using {self._label} from environment: {value}")
            return value
        raise ValueError(
            f"{self._label} not set for media operations. "
            f"Set via context or {self._env_var} environment variable."
        )


_username = _ContextValue("_current_username", "MEDIA_USERNAME", "Username")
_session_id = _ContextValue("_current_session_id", "MEDIA_SESSION_ID", "Session ID")

set_username = _username.set
reset_username = _username.reset
get_username = _username.get

set_session_id = _session_id.set
reset_session_id = _session_id.reset
get_session_id = _session_id.get

__all__ = [
    "set_username", "reset_username", "get_username",
    "set_session_id", "reset_session_id", "get_session_id",
]
