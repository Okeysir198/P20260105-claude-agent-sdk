"""STT client for speech-to-text services.

Decodes audio to raw PCM int16 before sending to the STT server:
  1. soundfile (WAV, FLAC, OGG Vorbis, AIFF)
  2. ffmpeg fallback (WebM, MP3, AAC, Opus, etc.)
"""
import asyncio
import logging
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

from .base_client import BaseServiceClient
from ..config import get_service_url

logger = logging.getLogger(__name__)


class STTClient(BaseServiceClient):
    """Client for Whisper V3 Turbo and Nemotron Speech STT engines."""

    def __init__(self, engine: str = "whisper_v3_turbo"):
        url = get_service_url(engine)
        super().__init__(url, api_key=None)
        self._engine = engine

    async def transcribe(
        self,
        audio_file: Path,
        language: str = "auto",
    ) -> dict:
        """Transcribe an audio file. Returns dict with text, confidence, duration_ms, and language."""
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file}")

        pcm_bytes = await asyncio.to_thread(self._to_pcm_int16, audio_file)

        result = await self._post_raw("/transcribe", content=pcm_bytes)

        return self._parse_response(result, language)

    @staticmethod
    def _to_pcm_int16(audio_file: Path) -> bytes:
        """Convert audio file to raw PCM int16 bytes at 16kHz mono."""
        data: np.ndarray | None = None
        sr: int = 16000

        try:
            data, sr = sf.read(audio_file, dtype="float64")
        except Exception:
            pass

        if data is None:
            try:
                logger.debug(f"soundfile can't decode {audio_file.name}, trying ffmpeg")
                result = subprocess.run(
                    [
                        "ffmpeg", "-i", str(audio_file),
                        "-f", "s16le", "-acodec", "pcm_s16le",
                        "-ar", "16000", "-ac", "1",
                        "-loglevel", "error",
                        "pipe:1",
                    ],
                    capture_output=True,
                    timeout=30,
                )
                if result.returncode == 0 and result.stdout:
                    logger.debug(f"ffmpeg decoded {audio_file.name} ({len(result.stdout)} bytes PCM)")
                    return result.stdout
                logger.warning(f"ffmpeg failed for {audio_file.name}: {result.stderr.decode(errors='replace')[:200]}")
            except FileNotFoundError:
                logger.warning("ffmpeg not found — cannot decode non-WAV audio formats")
            except subprocess.TimeoutExpired:
                logger.warning(f"ffmpeg timed out decoding {audio_file.name}")

            logger.debug(f"Sending {audio_file.name} as raw bytes")
            return audio_file.read_bytes()

        if data.ndim > 1:
            data = data.mean(axis=1)

        if sr != 16000:
            target_len = int(len(data) / sr * 16000)
            indices = np.linspace(0, len(data) - 1, target_len)
            data = np.interp(indices, np.arange(len(data)), data)
            logger.debug(f"Resampled {sr}Hz → 16000Hz ({len(data)} samples)")

        int16_data = (data * 32768).clip(-32768, 32767).astype(np.int16)
        return int16_data.tobytes()

    def _parse_response(self, result: dict, language: str) -> dict:
        """Parse Deepgram V1 response format into a standardized dict."""
        alternatives = result.get("channel", {}).get("alternatives", [])
        if alternatives:
            alt = alternatives[0]
            return {
                "text": alt.get("transcript", ""),
                "confidence": alt.get("confidence"),
                "duration_ms": result.get("duration"),
                "language": result.get("metadata", {}).get("language", language),
            }

        return {
            "text": result.get("text", ""),
            "confidence": None,
            "duration_ms": result.get("duration_ms"),
            "language": language,
        }
