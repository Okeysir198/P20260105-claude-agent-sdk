"""STT tool implementations.

Transcribe audio using Whisper V3 Turbo or Nemotron Speech engines.
"""
import copy
from pathlib import Path
from typing import Any

from .clients.stt_client import STTClient
from .config import STT_ENGINE_DEFINITIONS, STT_FORMATS
from .helpers import (
    check_service_health,
    get_session_context,
    handle_media_service_errors,
    make_tool_result,
    resolve_input_file,
    save_output_and_build_url,
)


async def list_stt_engines(inputs: dict[str, Any]) -> dict[str, Any]:
    """List available STT engines with real-time health status."""
    engines = copy.deepcopy(STT_ENGINE_DEFINITIONS)
    for engine in engines:
        engine["status"] = await check_service_health(engine["url"])
    return make_tool_result({"engines": engines})


@handle_media_service_errors("STT")
async def transcribe_audio(inputs: dict[str, Any]) -> dict[str, Any]:
    """Transcribe audio file."""
    file_path = inputs["file_path"]
    engine = inputs.get("engine", "whisper_v3_turbo")
    language = inputs.get("language", "auto")

    username, file_storage = get_session_context()
    session_id = file_storage._session_id
    full_path = resolve_input_file(file_path, file_storage, STT_FORMATS, "STT")

    async with STTClient(engine) as client:
        result = await client.transcribe(audio_file=full_path, language=language)

    output_filename = f"{Path(file_path).stem}_transcript.txt"
    relative_path, download_url = await save_output_and_build_url(
        file_storage, username, session_id, output_filename, result["text"].encode()
    )

    return make_tool_result({
        "text": result["text"],
        "output_path": relative_path,
        "download_url": download_url,
        "engine": engine,
        "confidence": result.get("confidence"),
        "duration_ms": result.get("duration_ms"),
        "language": result.get("language", language),
    })


__all__ = ["list_stt_engines", "transcribe_audio"]
