"""TTS tool implementations.

Synthesize speech using Kokoro, Supertonic, or Chatterbox engines.
"""
import copy
import time
from typing import Any

from claude_agent_sdk import tool

from .clients.tts_client import TTSClient
from .config import (
    MAX_TTS_TEXT_LENGTH,
    TTS_ENGINE_DEFINITIONS,
    VOICE_CLONE_FORMATS,
    get_voices_for_engine,
)
from .helpers import (
    check_service_health,
    get_session_context,
    handle_media_service_errors,
    make_tool_error,
    make_tool_result,
    resolve_input_file,
    save_output_and_build_url,
)


def estimate_audio_duration(audio_data: bytes, audio_format: str) -> int | None:
    """Estimate audio duration in milliseconds.

    For WAV files, parses headers for exact duration.
    For OGG/MP3, uses soundfile for accurate duration.

    Args:
        audio_data: Raw audio bytes
        audio_format: Audio format ("ogg", "wav", "mp3")

    Returns:
        Estimated duration in milliseconds, or None if unable to determine
    """
    if audio_format == "wav" and len(audio_data) > 44:
        byte_rate = int.from_bytes(audio_data[28:32], byteorder="little")
        if byte_rate > 0:
            data_size = len(audio_data) - 44
            return int((data_size / byte_rate) * 1000)

    if audio_format in ("ogg", "mp3"):
        try:
            import io
            import soundfile as sf
            data, sr = sf.read(io.BytesIO(audio_data))
            return int(len(data) / sr * 1000)
        except Exception:
            pass

    return None


@tool(
    name="list_tts_engines",
    description=(
        "List all available Text-to-Speech engines and their supported voices. "
        "ALWAYS call this first to see which engines are available and their voice options. "
        "Services run locally as Docker containers on localhost."
    ),
    input_schema={
        "type": "object",
        "properties": {},
        "required": []
    }
)
async def list_tts_engines(inputs: dict[str, Any]) -> dict[str, Any]:
    """List available TTS engines with real-time health status."""
    engines = copy.deepcopy(TTS_ENGINE_DEFINITIONS)
    for engine in engines:
        engine["status"] = await check_service_health(engine["url"])
    return make_tool_result({"engines": engines})


@tool(
    name="synthesize_speech",
    description=(
        "Convert text to speech using the specified TTS engine and voice. "
        "Returns the audio file path and format. "
        "All TTS services run locally as Docker containers.\n\n"
        "**Available Engines:**\n"
        "- supertonic_v1_1 (Primary): 10 local voices (M1-M5, F1-F5) + 11 Aura voices. Best quality.\n"
        "- kokoro: 7 local voices. Lightweight, multi-language (10 languages).\n"
        "- chatterbox_turbo: Voice cloning. Requires reference_audio_path.\n\n"
        "**Voice Examples:**\n"
        "- Supertonic: F1-F5 (female), M1-M5 (male), aura-asteria-en, aura-angus-en, etc.\n"
        "- Kokoro: af_heart, af_sky, af_bella (female), am_adam, am_michael (male), bf_emma (British female)\n\n"
        "**Parameters:**\n"
        "- speed: 0.7-2.0 (Supertonic), 0.5-2.0 (Kokoro). Default: 1.0\n"
        "- language: Language code (e.g., en-us, en-gb, es, fr, vi, zh, ja). Default: en-us\n"
        "- total_steps: 2-15 (Supertonic only, higher = better quality but slower)"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to synthesize into speech."
            },
            "engine": {
                "type": "string",
                "enum": ["supertonic_v1_1", "kokoro", "chatterbox_turbo"],
                "description": "TTS engine to use. Default: supertonic_v1_1 (recommended for best quality).",
                "default": "supertonic_v1_1"
            },
            "voice": {
                "type": "string",
                "description": "Voice ID. Examples: 'F1' (Supertonic female), 'M1' (Supertonic male), 'af_heart' (Kokoro female), 'am_adam' (Kokoro male)."
            },
            "speed": {
                "type": "number",
                "description": "Speech speed multiplier. Range: 0.7-2.0 for Supertonic, 0.5-2.0 for Kokoro. Default: 1.0",
                "default": 1.0
            },
            "language": {
                "type": "string",
                "description": "Language code (e.g., 'en-us', 'en-gb', 'es', 'fr', 'vi', 'zh', 'ja'). Default: en-us",
                "default": "en-us"
            },
            "total_steps": {
                "type": "integer",
                "description": "Inference steps for Supertonic only (2-15, higher = better quality but slower). Optional.",
                "minimum": 2,
                "maximum": 15
            },
            "reference_audio_path": {
                "type": "string",
                "description": "Path to reference audio file for voice cloning (required for Chatterbox Turbo)."
            }
        },
        "required": ["text"]
    }
)
@handle_media_service_errors("TTS")
async def synthesize_speech(inputs: dict[str, Any]) -> dict[str, Any]:
    """Synthesize speech from text."""
    text = inputs["text"]
    engine = inputs.get("engine", "supertonic_v1_1")
    voice = inputs.get("voice")
    speed = inputs.get("speed", 1.0)
    language = inputs.get("language", "en-us")
    total_steps = inputs.get("total_steps")
    reference_audio_raw = inputs.get("reference_audio_path")

    if len(text) > MAX_TTS_TEXT_LENGTH:
        return make_tool_error(
            f"Text too long ({len(text)} chars). Maximum: {MAX_TTS_TEXT_LENGTH} characters."
        )

    username, file_storage = get_session_context()
    session_id = file_storage._session_id

    # Resolve reference audio for voice cloning
    resolved_ref_path = None
    if reference_audio_raw:
        if engine != "chatterbox_turbo":
            return make_tool_error(
                "reference_audio_path is only supported with the 'chatterbox_turbo' engine."
            )
        resolved_ref_path = resolve_input_file(
            reference_audio_raw, file_storage, VOICE_CLONE_FORMATS, "synthesize_speech"
        )

    # Skip voice validation when using reference audio (voice cloning)
    if voice and not resolved_ref_path:
        available_voices = get_voices_for_engine(engine)
        if available_voices and voice not in available_voices:
            return make_tool_error(
                f"Unknown voice '{voice}' for engine '{engine}'. "
                f"Available: {', '.join(available_voices)}"
            )

    async with TTSClient(engine) as client:
        audio_data, audio_format, cloned_voice_id = await client.synthesize(
            text=text,
            voice=voice,
            speed=speed,
            language=language,
            total_steps=total_steps,
            reference_audio_path=resolved_ref_path,
        )

    output_filename = f"tts_{int(time.time())}.{audio_format}"
    relative_path, download_url = await save_output_and_build_url(
        file_storage, username, session_id, output_filename, audio_data
    )

    result = {
        "audio_path": relative_path,
        "download_url": download_url,
        "format": audio_format,
        "engine": engine,
        "voice": voice,
        "text": text,
        "duration_ms": estimate_audio_duration(audio_data, audio_format),
        "file_size_bytes": len(audio_data),
    }
    if cloned_voice_id:
        result["voice_cloned"] = True
        result["voice_id"] = cloned_voice_id
    return make_tool_result(result)


__all__ = ["list_tts_engines", "synthesize_speech"]
