"""MCP server for media processing tools (OCR, STT, TTS).

Registers tools with the Claude Agent SDK and manages per-request context
(username, session_id) via context variables with environment variable fallback.
"""
import contextvars
import logging
import os

from claude_agent_sdk import create_sdk_mcp_server

from agent.tools.media.ocr_tools import perform_ocr
from agent.tools.media.stt_tools import list_stt_engines, transcribe_audio
from agent.tools.media.tts_tools import list_tts_engines, synthesize_speech

logger = logging.getLogger(__name__)


class _ContextValue:
    """Thread-safe context variable with environment variable fallback.

    Tries the context variable first (in-process calls), then falls back
    to an environment variable (subprocess calls from SDK).
    """

    def __init__(self, name: str, env_var: str, label: str) -> None:
        self._var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
            name, default=None
        )
        self._env_var = env_var
        self._label = label

    def set(self, value: str) -> contextvars.Token[str | None]:
        """Set the value. Returns a token for resetting."""
        return self._var.set(value)

    def reset(self, token: contextvars.Token[str | None]) -> None:
        """Reset to previous value using a token from set()."""
        self._var.reset(token)

    def get(self) -> str:
        """Get the current value, falling back to environment variable."""
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

# Public API - preserve function signatures for backward compatibility
set_username = _username.set
reset_username = _username.reset
get_username = _username.get

set_session_id = _session_id.set
reset_session_id = _session_id.reset
get_session_id = _session_id.get

# MCP server registration
media_tools_server = create_sdk_mcp_server(
    name="media_tools",
    version="1.0.0",
    tools=[
        perform_ocr,
        list_stt_engines,
        transcribe_audio,
        list_tts_engines,
        synthesize_speech,
    ],
)

__all__ = [
    "media_tools_server",
    "set_username",
    "reset_username",
    "get_username",
    "set_session_id",
    "reset_session_id",
    "get_session_id",
]
