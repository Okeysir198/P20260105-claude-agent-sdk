"""Configuration for media processing services.

Service URLs and default settings for OCR, STT, and TTS services.
All services run as local Docker containers on localhost.
"""
import os
from pathlib import Path

# ==============================================================================
# Service URLs (all localhost Docker containers)
# ==============================================================================

# OCR Service - Ollama GLM-OCR (Vietnamese OCR with layout detection)
OCR_SERVICE_URL = "http://localhost:18013"

# STT Services - Speech-to-Text
STT_WHISPER_URL = "http://localhost:18050"      # Whisper V3 Turbo (~180-2200ms latency)
STT_NEMOTRON_URL = "http://localhost:18052"     # Nemotron Speech 0.6B (~14-15ms TTFB)

# TTS Services - Text-to-Speech
TTS_SUPERTONIC_URL = "http://localhost:18030"   # SupertonicTTS v1.1 (Deepgram Aura proxy)
TTS_CHATTERBOX_URL = "http://localhost:18033"   # Chatterbox Turbo (voice cloning)
TTS_KOKORO_URL = "http://localhost:18034"       # Kokoro TTS (lightweight multi-language)

# ==============================================================================
# API Keys (from environment)
# ==============================================================================

# Optional: OCR service API key (if authentication is enabled)
OCR_API_KEY = os.getenv("VLLM_API_KEY", "")

# TTS service: SupertonicTTS uses Deepgram API format (local service accepts dummy key)
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "dummy")

# ==============================================================================
# Default Settings
# ==============================================================================

# STT defaults
DEFAULT_STT_LANGUAGE = "auto"  # Auto-detect language
DEFAULT_STT_ENGINE = "whisper_v3_turbo"

# TTS defaults - Supertonic is primary (better quality, more features)
DEFAULT_TTS_ENGINE = "supertonic_v1_1"
DEFAULT_TTS_VOICE_SUPERTONIC = "F1"  # Supertonic default voice (female)
DEFAULT_TTS_VOICE_KOKORO = "af_heart"  # Kokoro default voice
DEFAULT_TTS_SPEED = 1.0
DEFAULT_TTS_FORMAT = "wav"

# Voice mappings for different TTS engines (from actual service APIs)
TTS_VOICES = {
    "kokoro": [
        # Female voices
        "af_heart", "af_sky", "af_bella",
        # Male voices
        "am_adam", "am_michael",
        # British female
        "bf_emma", "bf_george",
        # British male
        "bm_george", "bm_lewis"
    ],
    "supertonic": [
        # Female voices (F1-F5)
        "F1", "F2", "F3", "F4", "F5",
        # Male voices (M1-M5)
        "M1", "M2", "M3", "M4", "M5",
        # Aura voices (cloud models, also available)
        "aura-asteria-en", "aura-angus-en", "aura-daniel-en", "aura-hera-en",
        "aura-luna-en", "aura-river-en", "aura-stella-en",
        "aura-2-andromeda-en", "aura-2-athena-en", "aura-2-orion-en", "aura-2-perseus-en"
    ],
    "chatterbox": ["custom"],  # Voice cloning - uses reference audio
}

# Language codes for STT
STT_LANGUAGES = {
    "auto": "Auto-detect",
    "en": "English",
    "vi": "Vietnamese",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
}

# Supported file formats
OCR_FORMATS = ["pdf", "png", "jpg", "jpeg", "tiff", "bmp", "webp"]
STT_FORMATS = ["wav", "mp3", "m4a", "aac", "flac", "ogg", "opus", "webm"]
TTS_OUTPUT_FORMATS = ["wav", "mp3"]

# Request timeout (seconds)
REQUEST_TIMEOUT = 120


def get_service_url(engine: str) -> str:
    """Get service URL for a given engine.

    Args:
        engine: Engine identifier (e.g., "whisper_v3_turbo", "kokoro")

    Returns:
        Service base URL

    Raises:
        ValueError: If engine is unknown
    """
    urls = {
        # STT engines
        "whisper_v3_turbo": STT_WHISPER_URL,
        "nemotron_speech": STT_NEMOTRON_URL,
        # TTS engines
        "supertonic_v1_1": TTS_SUPERTONIC_URL,
        "chatterbox_turbo": TTS_CHATTERBOX_URL,
        "kokoro": TTS_KOKORO_URL,
    }

    if engine not in urls:
        raise ValueError(f"Unknown engine: {engine}. Available: {list(urls.keys())}")

    return urls[engine]


def get_voices_for_engine(engine: str) -> list[str]:
    """Get available voices for a TTS engine.

    Args:
        engine: TTS engine identifier

    Returns:
        List of voice IDs
    """
    engine_map = {
        "kokoro": "kokoro",
        "supertonic_v1_1": "supertonic",
        "chatterbox_turbo": "chatterbox",
    }

    key = engine_map.get(engine)
    return TTS_VOICES.get(key, [])
