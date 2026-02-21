"""Configuration for media processing services.

Service URLs and default settings for OCR, STT, and TTS services.
All services run as local Docker containers on localhost.
"""
import os

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
DEFAULT_TTS_FORMAT = "mp3"

# Voice mappings for different TTS engines (from actual service APIs)
TTS_VOICES = {
    "kokoro": [
        # American female
        "af_heart", "af_sky", "af_bella",
        # American male
        "am_adam", "am_michael",
        # British
        "bf_emma", "bf_george", "bm_george", "bm_lewis"
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
    "pt": "Portuguese",
    "ru": "Russian",
    "it": "Italian",
    "nl": "Dutch",
    "sv": "Swedish",
    "pl": "Polish",
}

# Supported file formats
OCR_FORMATS = ["pdf", "png", "jpg", "jpeg", "tiff", "bmp", "webp"]
STT_FORMATS = ["wav", "mp3", "m4a", "aac", "flac", "ogg", "opus", "webm"]
TTS_OUTPUT_FORMATS = ["wav", "mp3"]

# Engine metadata definitions (single source of truth for list_*_engines tools)
STT_ENGINE_DEFINITIONS = [
    {
        "id": "whisper_v3_turbo",
        "name": "Whisper Large V3 Turbo (Primary)",
        "description": "High-accuracy multilingual STT with ~180-2200ms latency. Supports 99 languages including English, Vietnamese, Chinese, Japanese, Korean.",
        "url": STT_WHISPER_URL,
        "supports_streaming": True,
        "languages": list(STT_LANGUAGES.keys()),
        "recommended": True,
        "latency_ms": "180-2200",
    },
    {
        "id": "nemotron_speech",
        "name": "Nemotron Speech 0.6B",
        "description": "Ultra-low latency STT with ~14-15ms time-to-first-byte. Requires NVIDIA GPU. English only.",
        "url": STT_NEMOTRON_URL,
        "supports_streaming": True,
        "languages": ["en"],
        "latency_ms": "14-15",
    },
]

TTS_ENGINE_DEFINITIONS = [
    {
        "id": "supertonic_v1_1",
        "name": "SupertonicTTS v1.1 (Primary)",
        "description": "High-quality TTS with 10 local voices (M1-M5 male, F1-F5 female) + 11 Aura cloud voices. Supports speed, language, encoding, and sample rate adjustment.",
        "url": TTS_SUPERTONIC_URL,
        "voices": TTS_VOICES["supertonic"],
        "output_format": "mp3",
        "parameters": ["speed", "language", "encoding", "sample_rate", "container", "total_steps"],
        "is_local": True,
        "recommended": True,
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
    },
]

# Maximum TTS text length
MAX_TTS_TEXT_LENGTH = 10000

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
    if key is None:
        return []
    return TTS_VOICES.get(key, [])
