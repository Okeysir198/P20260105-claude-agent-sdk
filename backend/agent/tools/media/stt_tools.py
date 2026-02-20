"""STT tool implementations.

Transcribe audio using Whisper V3 Turbo or Nemotron Speech engines.
"""
import logging
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool
from .clients.stt_client import STTClient
from .config import STT_WHISPER_URL, STT_NEMOTRON_URL

logger = logging.getLogger(__name__)


@tool(
    name="list_stt_engines",
    description=(
        "List all available Speech-to-Text engines and their capabilities. "
        "ALWAYS call this first to see which engines are available and their status. "
        "Services run locally as Docker containers on localhost."
    ),
    input_schema={
        "type": "object",
        "properties": {},
        "required": []
    }
)
async def list_stt_engines(inputs: dict[str, Any]) -> dict[str, Any]:
    """List available STT engines with detailed information."""
    engines = [
        {
            "id": "whisper_v3_turbo",
            "name": "Whisper Large V3 Turbo (Primary)",
            "description": "High-accuracy multilingual STT with ~180-2200ms latency. Supports 99 languages including English, Vietnamese, Chinese, Japanese, Korean.",
            "url": STT_WHISPER_URL,
            "supports_streaming": True,
            "languages": ["auto", "en", "vi", "zh", "ja", "ko", "es", "fr", "de", "pt", "ru", "it", "nl", "sv", "pl"],
            "status": "available",
            "recommended": True,
            "latency_ms": "180-2200"
        },
        {
            "id": "nemotron_speech",
            "name": "Nemotron Speech 0.6B",
            "description": "Ultra-low latency STT with ~14-15ms time-to-first-byte. Requires NVIDIA GPU. English only.",
            "url": STT_NEMOTRON_URL,
            "supports_streaming": True,
            "languages": ["en"],
            "status": "available",
            "latency_ms": "14-15"
        }
    ]
    return {"engines": engines}


@tool(
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
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the audio file to transcribe (relative to session's input directory, e.g., 'recording.wav')."
            },
            "engine": {
                "type": "string",
                "enum": ["whisper_v3_turbo", "nemotron_speech"],
                "description": "STT engine to use. Default: whisper_v3_turbo (recommended for multilingual support).",
                "default": "whisper_v3_turbo"
            },
            "language": {
                "type": "string",
                "description": "Language code for transcription (e.g., 'en', 'vi', 'zh', 'ja', 'ko', 'es', 'fr', 'de'). Use 'auto' for auto-detection. Default: auto",
                "default": "auto"
            }
        },
        "required": ["file_path"]
    }
)
async def transcribe_audio(inputs: dict[str, Any]) -> dict[str, Any]:
    """Transcribe audio file."""
    from .mcp_server import get_username
    from agent.core.file_storage import FileStorage

    username = get_username()
    file_path = inputs["file_path"]
    engine = inputs.get("engine", "whisper_v3_turbo")
    language = inputs.get("language", "auto")
    session_id = inputs.get("session_id", "default")

    file_storage = FileStorage(username=username, session_id=session_id)
    full_path = file_storage.get_session_dir() / "input" / file_path

    if not full_path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    # Call STT service
    stt_client = STTClient(engine)
    try:
        result = await stt_client.transcribe(
            audio_file=full_path,
            language=language
        )

        # Save transcript
        output_filename = f"{Path(file_path).stem}_transcript.txt"
        metadata = await file_storage.save_output_file(
            output_filename,
            result["text"].encode()
        )

        return {
            "text": result["text"],
            "output_path": f"{session_id}/output/{metadata.safe_name}",
            "engine": engine,
            "confidence": result.get("confidence"),
            "duration_ms": result.get("duration_ms"),
            "language": result.get("language", language)
        }
    finally:
        await stt_client.close()


__all__ = ["list_stt_engines", "transcribe_audio", "list_stt_engines_impl"]


async def list_stt_engines_impl() -> dict[str, Any]:
    """Implementation function for listing STT engines (for testing)."""
    engines = [
        {
            "id": "whisper_v3_turbo",
            "name": "Whisper Large V3 Turbo (Primary)",
            "description": "High-accuracy multilingual STT with ~180-2200ms latency. Supports 99 languages including English, Vietnamese, Chinese, Japanese, Korean.",
            "url": STT_WHISPER_URL,
            "supports_streaming": True,
            "languages": ["auto", "en", "vi", "zh", "ja", "ko", "es", "fr", "de", "pt", "ru", "it", "nl", "sv", "pl"],
            "status": "available",
            "recommended": True,
            "latency_ms": "180-2200"
        },
        {
            "id": "nemotron_speech",
            "name": "Nemotron Speech 0.6B",
            "description": "Ultra-low latency STT with ~14-15ms time-to-first-byte. Requires NVIDIA GPU. English only.",
            "url": STT_NEMOTRON_URL,
            "supports_streaming": True,
            "languages": ["en"],
            "status": "available",
            "latency_ms": "14-15"
        }
    ]
    return {"engines": engines}
