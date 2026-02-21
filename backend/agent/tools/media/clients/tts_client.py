"""TTS client for text-to-speech services.

Supports multiple TTS engines: Kokoro, Supertonic, and Chatterbox.
"""
import asyncio
import logging
import struct
from pathlib import Path
from typing import Tuple

from .base_client import BaseServiceClient
from ..config import (
    DEEPGRAM_API_KEY,
    get_service_url,
    get_voices_for_engine,
)

logger = logging.getLogger(__name__)


def _wrap_pcm_as_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, bits_per_sample: int = 16) -> bytes:
    """Wrap raw PCM data in a WAV header.

    Some TTS services return raw PCM even when container=wav is requested.
    This wraps the data with proper RIFF/WAV headers for browser playback.
    """
    byte_rate = sample_rate * channels * (bits_per_sample // 8)
    block_align = channels * (bits_per_sample // 8)
    data_size = len(pcm_data)

    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        36 + data_size,      # file size - 8
        b'WAVE',
        b'fmt ',
        16,                  # fmt chunk size
        1,                   # PCM format
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


class TTSClient(BaseServiceClient):
    """Client for TTS services.

    Supports multiple TTS engines:
    - Kokoro: Lightweight multi-language, local only
    - SupertonicTTS: Deepgram Aura proxy, requires API key
    - Chatterbox Turbo: Voice cloning with reference audio
    """

    def __init__(self, engine: str = "kokoro"):
        """Initialize the TTS client.

        Args:
            engine: TTS engine to use ("kokoro", "supertonic_v1_1", "chatterbox_turbo")

        Raises:
            ValueError: If engine is unknown
        """
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
    ) -> Tuple[bytes, str]:
        """Synthesize speech from text.

        Args:
            text: Text to synthesize
            voice: Voice ID or name (uses service default if None)
            speed: Speech speed multiplier
            language: Language code
            total_steps: Inference steps for Supertonic (2-15)
            reference_audio: Reference audio for voice cloning (Chatterbox only)

        Returns:
            Tuple of (audio_data, audio_format)

        Raises:
            ValueError: If engine is unknown or reference audio missing for Chatterbox
            httpx.HTTPStatusError: If TTS service request fails
        """
        if self._engine == "kokoro":
            return await self._synthesize_kokoro(text, voice, speed, language)
        elif self._engine == "supertonic_v1_1":
            return await self._synthesize_supertonic(text, voice, speed, language, total_steps)
        elif self._engine == "chatterbox_turbo":
            return await self._synthesize_chatterbox(text, voice, speed, reference_audio)
        else:
            raise ValueError(f"Unknown engine: {self._engine}")

    async def _synthesize_kokoro(
        self,
        text: str,
        voice: str | None,
        speed: float,
        language: str = "en-us",
    ) -> Tuple[bytes, str]:
        """Synthesize with Kokoro TTS.

        Uses Deepgram-compatible API: POST /v1/speak with JSON body.

        Args:
            text: Text to synthesize
            voice: Voice ID (e.g., "af_heart")
            speed: Speed multiplier (0.5-2.0)
            language: Language code

        Returns:
            Tuple of (audio_data, "wav")
        """
        # Build URL with query parameters
        # container=wav returns a proper WAV file with headers (playable in browsers)
        import urllib.parse
        params = {
            "model": voice or "af_heart",
            "speed": str(speed),
            "language": language,
            "encoding": "linear16",
            "sample_rate": "24000",
            "container": "wav"
        }
        url = f"{self.base_url}/v1/speak?{urllib.parse.urlencode(params)}"

        # Send request with JSON body
        response = await self._client.post(
            url,
            json={"text": text}
        )
        response.raise_for_status()

        return _ensure_wav(response.content, sample_rate=24000), "wav"

    async def _synthesize_supertonic(
        self,
        text: str,
        voice: str | None,
        speed: float,
        language: str = "en-us",
        total_steps: int | None = None,
    ) -> Tuple[bytes, str]:
        """Synthesize with SupertonicTTS (Deepgram Aura proxy).

        Args:
            text: Text to synthesize
            voice: Voice ID (M1-M5 for male, F1-F5 for female, or aura-xxx voices)
            speed: Speed multiplier (0.7-2.0)
            language: Language code
            total_steps: Inference steps (2-15, higher = better quality)

        Returns:
            Tuple of (audio_data, "mp3")
        """
        # Build URL with query parameters
        # container=wav returns a proper WAV file with headers (playable in browsers)
        import urllib.parse
        params = {
            "model": voice or "F1",
            "speed": str(speed),
            "language": language,
            "encoding": "linear16",
            "sample_rate": "24000",
            "container": "wav"
        }
        if total_steps is not None:
            params["total_steps"] = str(total_steps)

        url = f"{self.base_url}/v1/speak?{urllib.parse.urlencode(params)}"

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = await self._client.post(
            url,
            json={"text": text},
            headers=headers
        )
        response.raise_for_status()

        return _ensure_wav(response.content, sample_rate=24000), "wav"

    async def _synthesize_chatterbox(
        self,
        text: str,
        _voice: str | None,
        speed: float,
        reference_audio: bytes | None,
    ) -> Tuple[bytes, str]:
        """Synthesize with Chatterbox Turbo (voice cloning).

        Args:
            text: Text to synthesize
            _voice: Voice name (not used for custom cloning)
            speed: Speed multiplier
            reference_audio: Reference audio bytes for voice cloning

        Returns:
            Tuple of (audio_data, "wav")

        Raises:
            ValueError: If reference_audio is not provided
        """
        if not reference_audio:
            # Try to use default reference audio
            default_ref_path = Path(__file__).parent.parent / "voices" / "default_reference.wav"
            if default_ref_path.exists():
                reference_audio = await asyncio.to_thread(default_ref_path.read_bytes)
                logger.debug(f"Using default reference audio: {default_ref_path}")
            else:
                raise ValueError(
                    "Chatterbox Turbo requires reference audio for voice cloning. "
                    "Provide reference_audio or add default_reference.wav"
                )

        # Multipart request with reference audio
        files = {
            "reference": ("reference.wav", reference_audio, "audio/wav")
        }
        data = {
            "text": text,
            "speed": str(speed)
        }

        response = await self._post_multipart("/v1/speak", files=files, data=data)

        # Assume JSON response with audio field or bytes
        if isinstance(response, dict) and "audio" in response:
            import base64
            audio_data = base64.b64decode(response["audio"])
            return audio_data, "wav"

        # If we got here, the response is likely raw bytes from _post_multipart
        # that couldn't be parsed as JSON (shouldn't happen with current API)
        raise TypeError(f"Unexpected response type from Chatterbox: {type(response)}")

    def list_voices(self) -> list[dict]:
        """Get available voices for the current engine.

        Returns:
            List of voice info dicts with id, name, and language
        """
        voices = get_voices_for_engine(self._engine)

        if self._engine == "kokoro":
            return [
                {"id": v, "name": v, "language": "en"}
                for v in voices
            ]
        elif self._engine == "supertonic_v1_1":
            return [
                {"id": v, "name": f"Voice {v}", "language": "en"}
                for v in voices
            ]
        else:  # chatterbox_turbo
            return [
                {"id": "custom", "name": "Custom Cloned Voice", "language": "en"}
            ]
