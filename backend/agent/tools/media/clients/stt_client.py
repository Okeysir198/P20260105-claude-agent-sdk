"""STT client for speech-to-text services.

Supports Whisper V3 Turbo and Nemotron Speech engines.
The STT servers expect raw PCM int16 bytes on /transcribe.
Encoded files (Ogg, MP3, FLAC, etc.) are decoded via soundfile first;
raw PCM files are sent directly.
"""
import asyncio
import logging
from pathlib import Path

import numpy as np
import soundfile as sf

from .base_client import BaseServiceClient
from ..config import get_service_url

logger = logging.getLogger(__name__)


class STTClient(BaseServiceClient):
    """Client for STT services.

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
    ) -> dict:
        """Transcribe an audio file.

        Encoded formats (Ogg, MP3, FLAC, etc.) are decoded to PCM int16 first.
        Raw PCM files are sent directly.

        Returns dict with text, confidence, duration_ms, and language.

        Raises:
            FileNotFoundError: If audio file doesn't exist
            httpx.HTTPStatusError: If STT service request fails
        """
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file}")

        pcm_bytes = await asyncio.to_thread(self._to_pcm_int16, audio_file)

        result = await self._post_raw("/transcribe", content=pcm_bytes)

        return self._parse_response(result, language)

    @staticmethod
    def _to_pcm_int16(audio_file: Path) -> bytes:
        """Convert audio file to raw PCM int16 bytes at 16kHz mono.

        Tries soundfile decoding first (handles Ogg, MP3, FLAC, WAV, etc.).
        Falls back to sending raw bytes for files that are already raw PCM.
        """
        try:
            data, sr = sf.read(audio_file, dtype="float64")
        except Exception:
            # File is likely already raw PCM (e.g. TTS output saved without proper headers)
            logger.debug(f"soundfile can't decode {audio_file.name}, sending as raw PCM")
            return audio_file.read_bytes()

        # Mix to mono if stereo
        if data.ndim > 1:
            data = data.mean(axis=1)

        # Resample to 16kHz if needed
        if sr != 16000:
            target_len = int(len(data) / sr * 16000)
            indices = np.linspace(0, len(data) - 1, target_len)
            data = np.interp(indices, np.arange(len(data)), data)
            logger.debug(f"Resampled {sr}Hz → 16000Hz ({len(data)} samples)")

        # Convert to int16
        int16_data = (data * 32768).clip(-32768, 32767).astype(np.int16)
        return int16_data.tobytes()

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
