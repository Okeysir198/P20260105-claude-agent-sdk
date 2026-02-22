"""TTS client for text-to-speech services.

Supports multiple TTS engines: Kokoro, Supertonic, and Chatterbox.
All engines return raw PCM int16 which is converted to OGG Opus
for universal platform compatibility (WhatsApp, Telegram, web, etc.).
"""
import io
import logging
import struct
import urllib.parse
from pathlib import Path

from collections.abc import Callable

import numpy as np
import soundfile as sf

from .base_client import BaseServiceClient
from ..config import (
    DEEPGRAM_API_KEY,
    get_service_url,
    get_voices_for_engine,
)

logger = logging.getLogger(__name__)

# TTS services return raw PCM int16 at this sample rate
_TTS_SAMPLE_RATE = 24000


def _pcm_to_ogg_opus(pcm_data: bytes, sample_rate: int = _TTS_SAMPLE_RATE) -> bytes:
    """Convert raw PCM int16 bytes to OGG Opus for platform compatibility."""
    audio = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float64) / 32768.0
    buf = io.BytesIO()
    sf.write(buf, audio, sample_rate, format="OGG", subtype="OPUS")
    return buf.getvalue()


def _wrap_pcm_as_wav(
    pcm_data: bytes,
    sample_rate: int = _TTS_SAMPLE_RATE,
    channels: int = 1,
    bits_per_sample: int = 16,
) -> bytes:
    """Wrap raw PCM data in a WAV header (fallback if OGG encoding fails)."""
    byte_rate = sample_rate * channels * (bits_per_sample // 8)
    block_align = channels * (bits_per_sample // 8)
    data_size = len(pcm_data)

    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        36 + data_size,
        b'WAVE',
        b'fmt ',
        16,
        1,  # PCM format
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b'data',
        data_size,
    )
    return header + pcm_data


def _encode_output(raw_pcm: bytes, sample_rate: int = _TTS_SAMPLE_RATE) -> tuple[bytes, str]:
    """Encode raw PCM to OGG Opus, falling back to WAV on failure.

    Returns (audio_bytes, format_extension).
    """
    try:
        return _pcm_to_ogg_opus(raw_pcm, sample_rate), "ogg"
    except Exception as e:
        logger.warning(f"OGG Opus encoding failed, falling back to WAV: {e}")
        return _wrap_pcm_as_wav(raw_pcm, sample_rate), "wav"


# Default voices per engine
_DEFAULT_VOICES = {
    "kokoro": "af_heart",
    "supertonic_v1_1": "F1",
    "chatterbox_turbo": "default",
}


class TTSClient(BaseServiceClient):
    """Client for TTS services.

    Supports multiple TTS engines:
    - Kokoro: Lightweight multi-language, local only
    - SupertonicTTS: Deepgram Aura proxy, requires API key
    - Chatterbox Turbo: Voice cloning with reference audio
    """

    def __init__(self, engine: str = "chatterbox_turbo"):
        url = get_service_url(engine)
        # Only Supertonic requires API key
        api_key = DEEPGRAM_API_KEY if engine == "supertonic_v1_1" else None
        super().__init__(url, api_key=api_key)
        self._engine = engine

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        speed: float = 1.0,
        language: str = "en-us",
        total_steps: int | None = None,
        reference_audio_path: Path | None = None,
    ) -> tuple[bytes, str, str | None]:
        """Synthesize speech from text.

        Returns tuple of (audio_data, audio_format, voice_id_or_none).
        voice_id is returned when reference audio was uploaded for cloning.

        Raises:
            ValueError: If engine is unknown
            httpx.HTTPStatusError: If TTS service request fails
        """
        if self._engine in ("kokoro", "supertonic_v1_1"):
            data, fmt = await self._synthesize_deepgram_api(text, voice, speed, language, total_steps)
            return data, fmt, None
        if self._engine == "chatterbox_turbo":
            return await self._synthesize_chatterbox(text, voice, speed, reference_audio_path)
        raise ValueError(f"Unknown engine: {self._engine}")

    async def _synthesize_deepgram_api(
        self,
        text: str,
        voice: str | None,
        speed: float,
        language: str,
        total_steps: int | None = None,
    ) -> tuple[bytes, str]:
        """Synthesize with Deepgram-compatible API (Kokoro and Supertonic)."""
        default_voice = _DEFAULT_VOICES.get(self._engine, "af_heart")
        params: dict[str, str] = {
            "model": voice or default_voice,
            "speed": str(speed),
            "language": language,
            "encoding": "linear16",
            "sample_rate": str(_TTS_SAMPLE_RATE),
            "container": "none",
        }
        if total_steps is not None:
            params["total_steps"] = str(total_steps)

        url = f"{self.base_url}/v1/speak?{urllib.parse.urlencode(params)}"

        response = await self._client.post(
            url,
            json={"text": text},
            headers=self._auth_headers(),
        )
        response.raise_for_status()

        return _encode_output(response.content)

    async def _upload_voice(self, audio_path: Path) -> str:
        """Upload reference audio to Chatterbox and return voice_id."""
        audio_bytes = audio_path.read_bytes()
        suffix = audio_path.suffix or ".wav"
        name = audio_path.stem

        files = {"audio": (f"reference{suffix}", audio_bytes, f"audio/{suffix.lstrip('.')}")}
        data = {"name": name}

        response = await self._client.post(
            f"{self.base_url}/v1/voices",
            files=files,
            data=data,
        )
        response.raise_for_status()
        return response.json()["voice_id"]

    async def _synthesize_chatterbox(
        self,
        text: str,
        voice: str | None,
        speed: float,
        reference_audio_path: Path | None = None,
    ) -> tuple[bytes, str, str | None]:
        """Synthesize with Chatterbox Turbo (Deepgram-compatible API).

        Uses `voice` query param to select voice prompt on the server.
        If reference_audio_path is provided, uploads it first to get a voice_id.
        Falls back to default voice if none specified.
        """
        cloned_voice_id: str | None = None

        if reference_audio_path is not None:
            cloned_voice_id = await self._upload_voice(reference_audio_path)
            effective_voice = cloned_voice_id
        else:
            effective_voice = voice or _DEFAULT_VOICES.get(self._engine, "default")

        params: dict[str, str] = {
            "model": effective_voice,
            "encoding": "linear16",
            "sample_rate": str(_TTS_SAMPLE_RATE),
            "container": "none",
        }
        if speed != 1.0:
            params["speed"] = str(speed)

        url = f"{self.base_url}/v1/speak?{urllib.parse.urlencode(params)}"

        response = await self._client.post(
            url,
            json={"text": text},
            headers=self._auth_headers(),
        )
        response.raise_for_status()

        audio_data, audio_format = _encode_output(response.content)
        return audio_data, audio_format, cloned_voice_id

    def list_voices(self) -> list[dict]:
        """Get available voices for the current engine."""
        voices = get_voices_for_engine(self._engine)

        voice_formatters: dict[str, Callable[[str], dict]] = {
            "kokoro": lambda v: {"id": v, "name": v, "language": "en"},
            "supertonic_v1_1": lambda v: {"id": v, "name": f"Voice {v}", "language": "en"},
        }

        formatter = voice_formatters.get(self._engine)
        if formatter:
            return [formatter(v) for v in voices]

        # Chatterbox and other cloning engines
        return [{"id": "custom", "name": "Custom Cloned Voice", "language": "en"}]
