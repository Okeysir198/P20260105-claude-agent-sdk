"""STT client for speech-to-text services.

Supports Whisper V3 Turbo and Nemotron Speech engines via Deepgram V1 compatible API.
"""
import asyncio
import logging
from pathlib import Path

from .base_client import BaseServiceClient
from ..config import get_service_url

logger = logging.getLogger(__name__)


class STTClient(BaseServiceClient):
    """Client for STT services (Deepgram V1 compatible).

    Supports multiple STT engines with different latency/accuracy tradeoffs:
    - Whisper V3 Turbo: High accuracy, ~180-2200ms latency
    - Nemotron Speech: Ultra-low ~14-15ms TTFB, English only
    """

    def __init__(self, engine: str = "whisper_v3_turbo"):
        """Initialize the STT client.

        Args:
            engine: STT engine to use ("whisper_v3_turbo" or "nemotron_speech")

        Raises:
            ValueError: If engine is unknown
        """
        url = get_service_url(engine)
        super().__init__(url, api_key=None)  # STT services don't require auth
        self._engine = engine

    async def transcribe(
        self,
        audio_file: Path,
        language: str = "auto",
        smart_format: bool = True,
    ) -> dict:
        """Transcribe an audio file.

        Args:
            audio_file: Path to audio file (WAV, MP3, M4A, etc.)
            language: Language code (default: "auto" for detection)
            smart_format: Enable smart formatting (punctuation, capitalization)

        Returns:
            Dict with:
                - text: Transcribed text
                - confidence: Confidence score (0-1)
                - duration_ms: Audio duration in milliseconds
                - language: Detected language code

        Raises:
            FileNotFoundError: If audio file doesn't exist
            httpx.HTTPStatusError: If STT service request fails
        """
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file}")

        content_type = self._get_audio_content_type(audio_file)

        file_bytes = await asyncio.to_thread(audio_file.read_bytes)
        files = {"audio": (audio_file.name, file_bytes, content_type)}

        # Deepgram V1 compatible API format
        data = {
            "model": "general-2",  # Deepgram model name
            "language": language if language != "auto" else None,
            "smart_format": "true" if smart_format else "false",
        }

        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}

        result = await self._post_multipart("/transcribe", files=files, data=data)

        # Parse Deepgram V1 response format
        # Response: {"channel": {"alternatives": [{"transcript": "...", "confidence": 0.95}]}}
        try:
            channel = result.get("channel", {})
            alternatives = channel.get("alternatives", [])
            if alternatives:
                alternative = alternatives[0]
                transcript = alternative.get("transcript", "")
                confidence = alternative.get("confidence")

                return {
                    "text": transcript,
                    "confidence": confidence,
                    "duration_ms": result.get("duration"),
                    "language": result.get("metadata", {}).get("language", language),
                }
        except (KeyError, IndexError) as e:
            logger.warning(f"Unexpected STT response format: {e}")

        # Fallback for simple text responses
        return {
            "text": result.get("text", ""),
            "confidence": None,
            "duration_ms": result.get("duration_ms"),
            "language": language,
        }

    def _get_audio_content_type(self, audio_file: Path) -> str:
        """Get MIME type for audio file.

        Args:
            audio_file: Path to audio file

        Returns:
            MIME type string
        """
        ext = audio_file.suffix.lstrip(".").lower()

        mime_types = {
            "wav": "audio/wav",
            "mp3": "audio/mpeg",
            "m4a": "audio/mp4",
            "aac": "audio/aac",
            "flac": "audio/flac",
            "ogg": "audio/ogg",
            "opus": "audio/opus",
            "webm": "audio/webm",
        }

        return mime_types.get(ext, "audio/wav")
