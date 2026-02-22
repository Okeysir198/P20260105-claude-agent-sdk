"""Configuration for media processing services (OCR, STT, TTS).

All services run as local Docker containers on localhost.
"""
import os

# Service URLs
OCR_SERVICE_URL = "http://localhost:18013"       # Ollama GLM-OCR
STT_WHISPER_URL = "http://localhost:18050"       # Whisper V3 Turbo
STT_NEMOTRON_URL = "http://localhost:18052"      # Nemotron Speech 0.6B
TTS_SUPERTONIC_URL = "http://localhost:18030"    # SupertonicTTS v1.1
TTS_CHATTERBOX_URL = "http://localhost:18033"    # Chatterbox Turbo (voice cloning)
TTS_KOKORO_URL = "http://localhost:18034"        # Kokoro TTS

# API keys
OCR_API_KEY = os.getenv("VLLM_API_KEY", "")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "dummy")

# STT defaults
DEFAULT_STT_LANGUAGE = "auto"
DEFAULT_STT_ENGINE = "whisper_v3_turbo"

# TTS defaults
DEFAULT_TTS_ENGINE = "supertonic_v1_1"
DEFAULT_TTS_VOICE_SUPERTONIC = "F1"
DEFAULT_TTS_VOICE_KOKORO = "af_heart"
DEFAULT_TTS_SPEED = 1.0
DEFAULT_TTS_FORMAT = "mp3"

# Available voices per TTS engine
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
    "chatterbox": [
        "default", "female_warm", "female_bright", "female_heart",
        "female_british", "male_deep", "male_smooth", "male_adam",
    ],
}

# Supported STT languages
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
STT_FORMATS = ["wav", "mp3", "m4a", "aac", "flac", "ogg", "oga", "opus", "webm"]
TTS_OUTPUT_FORMATS = ["wav", "mp3"]
VOICE_CLONE_FORMATS = ["wav", "mp3", "ogg", "flac"]

# Engine metadata (single source of truth for list_*_engines tools)
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
        "output_format": "ogg",
        "parameters": ["speed", "language", "total_steps"],
        "is_local": True,
        "recommended": True,
    },
    {
        "id": "kokoro",
        "name": "Kokoro TTS",
        "description": "Lightweight multi-language TTS with 7 local voices. Supports 10 languages including English, Vietnamese, Chinese, Japanese.",
        "url": TTS_KOKORO_URL,
        "voices": TTS_VOICES["kokoro"],
        "output_format": "ogg",
        "parameters": ["speed", "language"],
        "languages": ["en", "en-us", "en-gb", "es", "fr", "it", "pt", "hi", "ja", "zh"],
        "is_local": True,
    },
    {
        "id": "chatterbox_turbo",
        "name": "Chatterbox Turbo",
        "description": "Voice cloning TTS with 8 built-in voice prompts. Upload a reference audio (~10s WAV/MP3/OGG/FLAC) via reference_audio_path to clone any voice. Produces OGG Opus output.",
        "url": TTS_CHATTERBOX_URL,
        "voices": TTS_VOICES["chatterbox"],
        "output_format": "ogg",
        "parameters": ["speed"],
        "is_local": True,
    },
]

# Maximum TTS text length
MAX_TTS_TEXT_LENGTH = 10000

# Request timeout (seconds)
REQUEST_TIMEOUT = 120


ENGINE_URLS = {
    "whisper_v3_turbo": STT_WHISPER_URL,
    "nemotron_speech": STT_NEMOTRON_URL,
    "supertonic_v1_1": TTS_SUPERTONIC_URL,
    "chatterbox_turbo": TTS_CHATTERBOX_URL,
    "kokoro": TTS_KOKORO_URL,
}

# Maps engine IDs to TTS_VOICES keys
_ENGINE_TO_VOICE_KEY = {
    "kokoro": "kokoro",
    "supertonic_v1_1": "supertonic",
    "chatterbox_turbo": "chatterbox",
}


def get_service_url(engine: str) -> str:
    """Get service URL for a given engine. Raises ValueError if unknown."""
    if engine not in ENGINE_URLS:
        raise ValueError(f"Unknown engine: {engine}. Available: {list(ENGINE_URLS.keys())}")
    return ENGINE_URLS[engine]


def get_voices_for_engine(engine: str) -> list[str]:
    """Get available voices for a TTS engine. Returns empty list if unknown."""
    key = _ENGINE_TO_VOICE_KEY.get(engine)
    if key is None:
        return []
    return TTS_VOICES.get(key, [])
