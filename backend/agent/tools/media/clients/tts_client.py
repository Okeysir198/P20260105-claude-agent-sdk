"""TTS client for text-to-speech services.

Supports multiple TTS engines: Kokoro, Supertonic, and Chatterbox.
"""
import logging
from typing import Tuple

from .base_client import BaseServiceClient
from ..config import (
    TTS_SUPERTONIC_URL,
    TTS_CHATTERBOX_URL,
    TTS_KOKORO_URL,
    DEEPGRAM_API_KEY,
    get_service_url,
    get_voices_for_engine,
)

logger = logging.getLogger(__name__)


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
        # Build URL with query parameters (use sensible defaults)
        import urllib.parse
        params = {
            "model": voice or "af_heart",
            "speed": str(speed),
            "language": language,
            "encoding": "linear16",
            "sample_rate": "24000",
            "container": "none"
        }
        url = f"{self.base_url}/v1/speak?{urllib.parse.urlencode(params)}"

        # Send request with JSON body
        response = await self._client.post(
            url,
            json={"text": text}
        )
        response.raise_for_status()

        return response.content, "wav"

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
        # Build URL with query parameters (use sensible defaults)
        import urllib.parse
        params = {
            "model": voice or "F1",
            "speed": str(speed),
            "language": language,
            "encoding": "linear16",
            "sample_rate": "24000",
            "container": "none"
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

        return response.content, "mp3"

    async def _synthesize_chatterbox(
        self,
        text: str,
        voice: str,
        speed: float,
        reference_audio: bytes | None,
    ) -> Tuple[bytes, str]:
        """Synthesize with Chatterbox Turbo (voice cloning).

        Args:
            text: Text to synthesize
            voice: Voice name (not used for custom cloning)
            speed: Speed multiplier
            reference_audio: Reference audio bytes for voice cloning

        Returns:
            Tuple of (audio_data, "wav")

        Raises:
            ValueError: If reference_audio is not provided
        """
        if not reference_audio:
            # Try to use default reference audio
            default_ref_path = Path("backend/agent/tools/media/voices/default_reference.wav")
            if default_ref_path.exists():
                reference_audio = default_ref_path.read_bytes()
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

        # If we got here, the response might be bytes directly
        return response, "wav"

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
