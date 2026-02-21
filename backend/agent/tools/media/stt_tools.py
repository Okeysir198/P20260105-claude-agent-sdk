"""STT tool implementations.

Transcribe audio using Whisper V3 Turbo or Nemotron Speech engines.
"""
import copy
import logging
from pathlib import Path
from typing import Any

import httpx
from claude_agent_sdk import tool
from .clients.stt_client import STTClient
from .helpers import sanitize_file_path, validate_file_format, make_tool_result, make_tool_error
from .config import STT_FORMATS

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
    """List available STT engines with real-time health status."""
    from .helpers import check_service_health
    from .config import STT_ENGINE_DEFINITIONS

    engines = copy.deepcopy(STT_ENGINE_DEFINITIONS)
    for engine in engines:
        engine["status"] = await check_service_health(engine["url"])
    return make_tool_result({"engines": engines})


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
    try:
        from .mcp_server import get_username, get_session_id
        from agent.core.file_storage import FileStorage
        from api.services.file_download_token import create_download_token, build_download_url

        username = get_username()
        session_id = get_session_id()
        file_path = inputs["file_path"]
        engine = inputs.get("engine", "whisper_v3_turbo")
        language = inputs.get("language", "auto")

        file_storage = FileStorage(username=username, session_id=session_id)
        input_dir = file_storage.get_session_dir() / "input"
        full_path = sanitize_file_path(file_path, input_dir)
        validate_file_format(full_path, STT_FORMATS, "STT")

        if not full_path.exists():
            return make_tool_error(f"Audio file not found: {file_path}")

        async with STTClient(engine) as client:
            result = await client.transcribe(
                audio_file=full_path,
                language=language
            )

        output_filename = f"{Path(file_path).stem}_transcript.txt"
        metadata = await file_storage.save_output_file(
            output_filename,
            result["text"].encode()
        )

        relative_path = f"{session_id}/output/{metadata.safe_name}"
        token = create_download_token(
            username=username,
            cwd_id=session_id,
            relative_path=relative_path,
            expire_hours=24
        )
        download_url = build_download_url(token)

        return make_tool_result({
            "text": result["text"],
            "output_path": relative_path,
            "download_url": download_url,
            "engine": engine,
            "confidence": result.get("confidence"),
            "duration_ms": result.get("duration_ms"),
            "language": result.get("language", language)
        })
    except ValueError as e:
        return make_tool_error(str(e))
    except httpx.ConnectError:
        return make_tool_error("Cannot connect to STT service. Is the Docker container running?")
    except httpx.TimeoutException:
        return make_tool_error("STT service timed out (120s). Audio file may be too large.")
    except httpx.HTTPStatusError as e:
        return make_tool_error(f"STT service error: {e.response.status_code}")
    except Exception as e:
        logger.exception("Unexpected error in transcribe_audio")
        return make_tool_error(f"Unexpected error: {e}")


__all__ = ["list_stt_engines", "transcribe_audio"]
