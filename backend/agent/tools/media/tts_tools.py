"""TTS tool implementations.

Synthesize speech using Kokoro, Supertonic, or Chatterbox engines.
"""
import logging
import time
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool
from .clients.tts_client import TTSClient
from .config import (
    TTS_SUPERTONIC_URL,
    TTS_CHATTERBOX_URL,
    TTS_KOKORO_URL,
    TTS_VOICES,
)

logger = logging.getLogger(__name__)


def estimate_audio_duration(audio_data: bytes, audio_format: str) -> int:
    """Estimate audio duration in milliseconds (simplified).

    Args:
        audio_data: Raw audio bytes
        audio_format: Audio format ("mp3" or "wav")

    Returns:
        Estimated duration in milliseconds
    """
    # Rough estimate: 1 second per 16KB for MP3, 32KB for WAV
    # This is a simplified calculation - actual duration depends on bitrate/sample rate
    if audio_format == "mp3":
        return len(audio_data) // 16
    else:  # wav
        return len(audio_data) // 32


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
    """List available TTS engines with detailed information."""
    engines = [
        {
            "id": "supertonic_v1_1",
            "name": "SupertonicTTS v1.1 (Primary)",
            "description": "High-quality TTS with 10 local voices (M1-M5 male, F1-F5 female) + 11 Aura cloud voices. Supports speed, language, encoding, and sample rate adjustment.",
            "url": TTS_SUPERTONIC_URL,
            "voices": TTS_VOICES["supertonic"],
            "output_format": "mp3",
            "parameters": ["speed", "language", "encoding", "sample_rate", "container", "total_steps"],
            "is_local": True,
            "status": "available",
            "recommended": True
        },
        {
            "id": "kokoro",
            "name": "Kokoro TTS",
            "description": "Lightweight multi-language TTS with 7 local voices. Supports 10 languages including English, Vietnamese, Chinese, Japanese.",
            "url": TTS_KOKORO_URL,
            "voices": TTS_VOICES["kokoro"],
            "output_format": "wav",
            "parameters": ["speed", "language", "encoding", "sample_rate", "container"],
            "languages": ["en", "en-us", "en-gb", "es", "fr", "it", "pt", "hi", "ja", "zh"],
            "is_local": True,
            "status": "available"
        },
        {
            "id": "chatterbox_turbo",
            "name": "Chatterbox Turbo",
            "description": "Voice cloning TTS. Requires reference audio file to clone voice. Produces WAV output.",
            "url": TTS_CHATTERBOX_URL,
            "voices": ["custom_voice_cloning"],
            "output_format": "wav",
            "parameters": ["speed"],
            "requires_reference_audio": True,
            "is_local": True,
            "status": "available"
        }
    ]
    return {"engines": engines}


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
async def synthesize_speech(inputs: dict[str, Any]) -> dict[str, Any]:
    """Synthesize speech from text."""
    from .mcp_server import get_username, get_session_id
    from agent.core.file_storage import FileStorage
    from api.services.file_download_token import create_download_token, build_download_url

    username = get_username()
    session_id = get_session_id()
    text = inputs["text"]
    engine = inputs.get("engine", "supertonic_v1_1")
    voice = inputs.get("voice")
    speed = inputs.get("speed", 1.0)
    language = inputs.get("language", "en-us")
    total_steps = inputs.get("total_steps")

    file_storage = FileStorage(username=username, session_id=session_id)
    reference_path = inputs.get("reference_audio_path")

    # Load reference audio if specified
    reference_data = None
    if reference_path:
        full_ref_path = file_storage.get_session_dir() / "input" / reference_path
        if full_ref_path.exists():
            reference_data = full_ref_path.read_bytes()

    # Call TTS service with parameters
    tts_client = TTSClient(engine)
    try:
        audio_data, audio_format = await tts_client.synthesize(
            text=text,
            voice=voice,
            speed=speed,
            language=language,
            total_steps=total_steps,
            reference_audio=reference_data
        )

        # Save audio to output directory
        output_filename = f"tts_{int(time.time())}.{audio_format}"
        metadata = await file_storage.save_output_file(output_filename, audio_data)

        # Create download token and URL (24 hour expiry)
        relative_path = f"{session_id}/output/{metadata.safe_name}"
        token = create_download_token(
            username=username,
            cwd_id=session_id,
            relative_path=relative_path,
            expire_hours=24
        )
        download_url = build_download_url(token)

        return {
            "audio_path": relative_path,
            "download_url": download_url,
            "format": audio_format,
            "engine": engine,
            "voice": voice,
            "text": text,
            "duration_ms": estimate_audio_duration(audio_data, audio_format),
            "file_size_bytes": len(audio_data)
        }
    finally:
        await tts_client.close()


__all__ = ["list_tts_engines", "synthesize_speech", "list_tts_engines_impl"]


async def list_tts_engines_impl() -> dict[str, Any]:
    """Implementation function for listing TTS engines (for testing)."""
    engines = [
        {
            "id": "supertonic_v1_1",
            "name": "SupertonicTTS v1.1",
            "description": "Deepgram Aura proxy with voice mapping (local service with dummy API key)",
            "url": TTS_SUPERTONIC_URL,
            "voices": TTS_VOICES["supertonic"],
            "output_format": "mp3",
            "requires_api_key": True,
            "is_local": True,
            "status": "available"
        },
        {
            "id": "chatterbox_turbo",
            "name": "Chatterbox Turbo",
            "description": "Voice cloning with reference audio (local service, requires reference audio)",
            "url": TTS_CHATTERBOX_URL,
            "voices": ["custom_voice_cloning"],
            "output_format": "wav",
            "requires_reference_audio": True,
            "is_local": True,
            "status": "available"
        },
        {
            "id": "kokoro",
            "name": "Kokoro TTS",
            "description": "Lightweight multi-language TTS (local service)",
            "url": TTS_KOKORO_URL,
            "voices": TTS_VOICES["kokoro"],
            "languages": ["en", "en-us", "en-gb", "es", "fr", "it", "pt", "hi", "ja", "zh"],
            "output_format": "wav",
            "is_local": True,
            "status": "available"
        }
    ]
    return {"engines": engines}
