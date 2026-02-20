"""MCP server for media processing tools (OCR, STT, TTS).

Registers OCR, speech-to-text, and text-to-speech tools with the Claude Agent SDK.
Provides tools for extracting text from images, transcribing audio, and synthesizing speech.
"""
import contextvars
import logging
from typing import Any

from claude_agent_sdk import tool, create_sdk_mcp_server

from agent.tools.media.ocr_tools import perform_ocr
from agent.tools.media.stt_tools import list_stt_engines, transcribe_audio
from agent.tools.media.tts_tools import list_tts_engines, synthesize_speech

logger = logging.getLogger(__name__)


# Thread-safe context variable for current username
_current_username: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "_current_username", default=None
)


def set_username(username: str) -> contextvars.Token[str | None]:
    """Set the current username for media operations. Returns a token for resetting."""
    return _current_username.set(username)


def reset_username(token: contextvars.Token[str | None]) -> None:
    """Reset username to its previous value using a token from set_username."""
    _current_username.reset(token)


def get_username() -> str:
    """Get the current username for media operations.

    First tries context variable (for in-process calls), then falls back to
    environment variable MEDIA_USERNAME (for subprocess calls from SDK).
    """
    # Try context variable first (for direct in-process calls)
    username = _current_username.get()
    if username:
        return username

    # Fall back to environment variable (for SDK subprocess calls)
    import os
    username = os.environ.get("MEDIA_USERNAME")
    if username:
        logger.debug(f"Using username from environment: {username}")
        return username

    raise ValueError("Username not set for media operations. Call set_username() first or set MEDIA_USERNAME environment variable.")


# ======================================================================
# WORKFLOW GUIDE (embedded in tool descriptions so the agent learns the pattern)
#
# OCR: perform_ocr → extract text from images/PDFs
# STT: list_stt_engines → transcribe_audio
# TTS: list_tts_engines → synthesize_speech
# ======================================================================


# Create MCP server
media_tools_server = create_sdk_mcp_server(
    name="media_tools",
    version="1.0.0",
    tools=[
        # OCR tools
        perform_ocr,
        # STT tools
        list_stt_engines,
        transcribe_audio,
        # TTS tools
        list_tts_engines,
        synthesize_speech,
    ]
)


__all__ = [
    "media_tools_server",
    "set_username",
    "reset_username",
    "get_username",
]
