"""STT client for speech-to-text services.

Supports Whisper V3 Turbo and Nemotron Speech engines via Deepgram V1 compatible API.
"""
import asyncio
import logging
from pathlib import Path

from .base_client import BaseServiceClient, get_mime_type
from ..config import get_service_url

logger = logging.getLogger(__name__)


class STTClient(BaseServiceClient):
    """Client for STT services (Deepgram V1 compatible).

    Supports multiple STT engines with different latency/accuracy tradeoffs:
    - Whisper V3 Turbo: High accuracy, ~180-2200ms latency
    - Nemotron Speech: Ultra-low ~14-15ms TTFB, English only
    """

    def __init__(self, engine: str = "whisper_v3_turbo"):
        url = get_service_url(engine)
        super().__init__(url, api_key=None)
        self._engine = engine

    async def transcribe(
        self,
        audio_file: Path,
        language: str = "auto",
        smart_format: bool = True,
    ) -> dict:
        """Transcribe an audio file.

        Returns dict with text, confidence, duration_ms, and language.

        Raises:
            FileNotFoundError: If audio file doesn't exist
            httpx.HTTPStatusError: If STT service request fails
        """
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file}")

        content_type = get_mime_type(audio_file.name, fallback="audio/wav")

        file_bytes = await asyncio.to_thread(audio_file.read_bytes)
        files = {"audio": (audio_file.name, file_bytes, content_type)}

        # Deepgram V1 compatible API format
        data: dict[str, str] = {
            "model": "general-2",
            "smart_format": "true" if smart_format else "false",
        }
        if language != "auto":
            data["language"] = language

        result = await self._post_multipart("/transcribe", files=files, data=data)

        return self._parse_response(result, language)

    def _parse_response(self, result: dict, language: str) -> dict:
        """Parse Deepgram V1 response format into a standardized dict."""
        # Response: {"channel": {"alternatives": [{"transcript": "...", "confidence": 0.95}]}}
        alternatives = result.get("channel", {}).get("alternatives", [])
        if alternatives:
            alt = alternatives[0]
            return {
                "text": alt.get("transcript", ""),
                "confidence": alt.get("confidence"),
                "duration_ms": result.get("duration"),
                "language": result.get("metadata", {}).get("language", language),
            }

        # Fallback for simple text responses
        return {
            "text": result.get("text", ""),
            "confidence": None,
            "duration_ms": result.get("duration_ms"),
            "language": language,
        }
