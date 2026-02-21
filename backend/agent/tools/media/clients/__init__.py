"""HTTP/WebSocket clients for media processing services."""

from .base_client import BaseServiceClient
from .ocr_client import OCRClient
from .stt_client import STTClient
from .tts_client import TTSClient

__all__ = ["BaseServiceClient", "OCRClient", "STTClient", "TTSClient"]
