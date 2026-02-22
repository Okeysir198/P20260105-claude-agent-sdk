"""Standalone stdio MCP server for media processing tools (OCR, STT, TTS).

Runs as a subprocess speaking JSON-RPC over stdin/stdout.
Reads MEDIA_USERNAME and MEDIA_SESSION_ID from environment variables.

Usage:
    python -m media_tools.stdio_server
"""
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

from media_tools.ocr_tools import perform_ocr
from media_tools.stt_tools import list_stt_engines, transcribe_audio
from media_tools.tts_tools import list_tts_engines, synthesize_speech
from media_tools.send_file import send_file_to_chat

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

mcp = FastMCP("media_tools")


def _ensure_env(var: str) -> str:
    """Get required environment variable or raise."""
    value = os.environ.get(var)
    if not value:
        raise ValueError(f"Environment variable {var} is required but not set")
    return value


def _setup_context() -> None:
    """Set up media tools context from environment variables.

    Sets the contextvars used by helpers.get_session_context() so that
    existing tool implementations work unchanged.
    """
    from media_tools.context import set_username, set_session_id

    username = _ensure_env("MEDIA_USERNAME")
    session_id = _ensure_env("MEDIA_SESSION_ID")
    set_username(username)
    set_session_id(session_id)


# --- Tool registrations ---
# Each wraps the existing async function.
# The existing functions accept dict inputs and return dict results.

@mcp.tool(
    name="perform_ocr",
    description=(
        "Extract text from images or PDF documents using OCR. "
        "Supports PDF, PNG, JPG, JPEG, TIFF, BMP, WEBP formats. "
        "Returns structured text with layout detection, semantic tags, and page separators. "
        "Optionally applies Vietnamese text corrections if enabled. "
        "Input files should be uploaded via the file upload API and will be processed from the session's file storage. "
        "The file path should be relative to the session's input directory (e.g., 'document.pdf')."
    ),
)
async def tool_perform_ocr(
    file_path: str,
    apply_vietnamese_corrections: bool = False,
) -> dict:
    """Perform OCR on a file."""
    _setup_context()
    return await perform_ocr({
        "file_path": file_path,
        "apply_vietnamese_corrections": apply_vietnamese_corrections,
    })


@mcp.tool(
    name="list_stt_engines",
    description=(
        "List all available Speech-to-Text engines and their capabilities. "
        "ALWAYS call this first to see which engines are available and their status. "
        "Services run locally as Docker containers on localhost."
    ),
)
async def tool_list_stt_engines() -> dict:
    """List available STT engines with real-time health status."""
    return await list_stt_engines({})


@mcp.tool(
    name="transcribe_audio",
    description=(
        "Transcribe an audio file to text using the specified STT engine. "
        "Supports WAV, MP3, M4A, AAC, FLAC, OGG, OPUS, WEBM and other common audio formats. "
        "Audio files should be uploaded via the file upload API first. "
        "The file path should be relative to the session's input directory (e.g., 'recording.wav').\n\n"
        "**Available Engines:**\n"
        "- whisper_v3_turbo (Primary): Multilingual, supports 99 languages including English, Vietnamese, Chinese, Japanese. Latency: 180-2200ms\n"
        "- nemotron_speech: Ultra-low latency (~14-15ms), English only\n\n"
        "**Language Codes:** en, vi, zh, ja, ko, es, fr, de, pt, ru, it, nl, sv, pl, or 'auto' for auto-detection"
    ),
)
async def tool_transcribe_audio(
    file_path: str,
    engine: str = "whisper_v3_turbo",
    language: str = "auto",
) -> dict:
    """Transcribe audio file."""
    _setup_context()
    return await transcribe_audio({
        "file_path": file_path,
        "engine": engine,
        "language": language,
    })


@mcp.tool(
    name="list_tts_engines",
    description=(
        "List all available Text-to-Speech engines and their supported voices. "
        "ALWAYS call this first to see which engines are available and their voice options. "
        "Services run locally as Docker containers on localhost."
    ),
)
async def tool_list_tts_engines() -> dict:
    """List available TTS engines with real-time health status."""
    return await list_tts_engines({})


@mcp.tool(
    name="synthesize_speech",
    description=(
        "Convert text to speech using the specified TTS engine and voice. "
        "Returns the audio file path and format. "
        "All TTS services run locally as Docker containers.\n\n"
        "**Available Engines:**\n"
        "- chatterbox_turbo (Primary): Voice cloning with 8 built-in voices. Upload reference audio to clone any voice.\n"
        "- supertonic_v1_1: 10 local voices (M1-M5, F1-F5) + 11 Aura voices. Best quality.\n"
        "- kokoro: 7 local voices. Lightweight, multi-language (10 languages).\n\n"
        "**Voice Examples:**\n"
        "- Supertonic: F1-F5 (female), M1-M5 (male), aura-asteria-en, aura-angus-en, etc.\n"
        "- Kokoro: af_heart, af_sky, af_bella (female), am_adam, am_michael (male), bf_emma (British female)\n\n"
        "**Parameters:**\n"
        "- speed: 0.7-2.0 (Supertonic), 0.5-2.0 (Kokoro). Default: 1.0\n"
        "- language: Language code (e.g., en-us, en-gb, es, fr, vi, zh, ja). Default: en-us\n"
        "- total_steps: 2-15 (Supertonic only, higher = better quality but slower)"
    ),
)
async def tool_synthesize_speech(
    text: str,
    engine: str = "chatterbox_turbo",
    voice: str | None = None,
    speed: float = 1.0,
    language: str = "en-us",
    total_steps: int | None = None,
    reference_audio_path: str | None = None,
) -> dict:
    """Synthesize speech from text."""
    _setup_context()
    inputs: dict = {
        "text": text,
        "engine": engine,
        "speed": speed,
        "language": language,
    }
    if voice is not None:
        inputs["voice"] = voice
    if total_steps is not None:
        inputs["total_steps"] = total_steps
    if reference_audio_path is not None:
        inputs["reference_audio_path"] = reference_audio_path
    return await synthesize_speech(inputs)


@mcp.tool(
    name="send_file_to_chat",
    description=(
        "Send a file from the session directory to the user's chat. "
        "Use this to deliver generated files (audio, images, documents, etc.) directly to the user. "
        "The file must exist in the session directory (input/, output/, or root).\n\n"
        "**Parameters:**\n"
        "- file_path: Relative path within the session directory "
        "(e.g., 'output/tts_123.wav', 'input/document.pdf', 'report.txt')"
    ),
)
async def tool_send_file_to_chat(file_path: str) -> dict:
    """Send a file to the user's chat."""
    _setup_context()
    return await send_file_to_chat({"file_path": file_path})


if __name__ == "__main__":
    mcp.run()
