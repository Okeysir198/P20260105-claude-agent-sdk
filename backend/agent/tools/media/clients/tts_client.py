"""TTS client for text-to-speech services.

Supports multiple TTS engines: Kokoro, Supertonic, and Chatterbox.
"""
import asyncio
import logging
import struct
import urllib.parse
from pathlib import Path

from collections.abc import Callable

from .base_client import BaseServiceClient
from ..config import (
    DEEPGRAM_API_KEY,
    get_service_url,
    get_voices_for_engine,
)

logger = logging.getLogger(__name__)


def _wrap_pcm_as_wav(
    pcm_data: bytes,
    sample_rate: int = 24000,
    channels: int = 1,
    bits_per_sample: int = 16,
) -> bytes:
    """Wrap raw PCM data in a WAV header for browser playback."""
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


def _ensure_wav(audio_data: bytes, sample_rate: int = 24000) -> bytes:
    """Ensure audio data has WAV headers. Wraps raw PCM if needed."""
    if audio_data[:4] == b'RIFF':
        return audio_data
    return _wrap_pcm_as_wav(audio_data, sample_rate=sample_rate)


# Default voices per engine
_DEFAULT_VOICES = {
    "kokoro": "af_heart",
    "supertonic_v1_1": "F1",
}


class TTSClient(BaseServiceClient):
    """Client for TTS services.

    Supports multiple TTS engines:
    - Kokoro: Lightweight multi-language, local only
    - SupertonicTTS: Deepgram Aura proxy, requires API key
    - Chatterbox Turbo: Voice cloning with reference audio
    """

    def __init__(self, engine: str = "kokoro"):
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
        reference_audio: bytes | None = None,
    ) -> tuple[bytes, str]:
        """Synthesize speech from text.

        Returns tuple of (audio_data, audio_format).

        Raises:
            ValueError: If engine is unknown or reference audio missing for Chatterbox
            httpx.HTTPStatusError: If TTS service request fails
        """
        if self._engine in ("kokoro", "supertonic_v1_1"):
            return await self._synthesize_deepgram_api(text, voice, speed, language, total_steps)
        if self._engine == "chatterbox_turbo":
            return await self._synthesize_chatterbox(text, speed, reference_audio)
        raise ValueError(f"Unknown engine: {self._engine}")

    async def _synthesize_deepgram_api(
        self,
        text: str,
        voice: str | None,
        speed: float,
        language: str,
        total_steps: int | None = None,
    ) -> tuple[bytes, str]:
        """Synthesize with Deepgram-compatible API (Kokoro and Supertonic).

        Both engines use the same POST /v1/speak endpoint with query params.
        """
        default_voice = _DEFAULT_VOICES.get(self._engine, "af_heart")
        params: dict[str, str] = {
            "model": voice or default_voice,
            "speed": str(speed),
            "language": language,
            "encoding": "linear16",
            "sample_rate": "24000",
            "container": "wav",
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

        return _ensure_wav(response.content, sample_rate=24000), "wav"

    async def _synthesize_chatterbox(
        self,
        text: str,
        speed: float,
        reference_audio: bytes | None,
    ) -> tuple[bytes, str]:
        """Synthesize with Chatterbox Turbo (voice cloning).

        Raises:
            ValueError: If reference_audio is not provided and no default exists
        """
        if not reference_audio:
            default_ref_path = Path(__file__).parent.parent / "voices" / "default_reference.wav"
            if default_ref_path.exists():
                reference_audio = await asyncio.to_thread(default_ref_path.read_bytes)
                logger.debug(f"Using default reference audio: {default_ref_path}")
            else:
                raise ValueError(
                    "Chatterbox Turbo requires reference audio for voice cloning. "
                    "Provide reference_audio or add default_reference.wav"
                )

        files = {"reference": ("reference.wav", reference_audio, "audio/wav")}
        data = {"text": text, "speed": str(speed)}

        response = await self._post_multipart("/v1/speak", files=files, data=data)

        if isinstance(response, dict) and "audio" in response:
            import base64
            audio_data = base64.b64decode(response["audio"])
            return audio_data, "wav"

        raise TypeError(f"Unexpected response type from Chatterbox: {type(response)}")

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
