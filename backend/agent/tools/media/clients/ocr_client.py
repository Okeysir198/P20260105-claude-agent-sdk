"""OCR client for Ollama GLM-OCR service.

Extracts text from images and PDFs with Vietnamese correction support.
"""
import asyncio
import logging
import time
from pathlib import Path

from .base_client import BaseServiceClient, get_mime_type
from ..config import OCR_SERVICE_URL, OCR_API_KEY

logger = logging.getLogger(__name__)


class OCRClient(BaseServiceClient):
    """Client for Ollama GLM-OCR service.

    Provides OCR capabilities for images and PDFs with layout detection,
    semantic tagging, and optional Vietnamese text corrections.
    """

    def __init__(self, base_url: str = OCR_SERVICE_URL, api_key: str | None = None):
        super().__init__(base_url, api_key or OCR_API_KEY or None)

    async def process_file(
        self,
        file_path: Path,
        apply_vietnamese_corrections: bool = False,
    ) -> dict:
        """Process a file through OCR.

        Returns dict with text, pages, and processing_time_ms.

        Raises:
            FileNotFoundError: If file doesn't exist
            httpx.HTTPStatusError: If OCR service request fails
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content_type = get_mime_type(file_path.name)
        start_time = time.time()

        file_bytes = await asyncio.to_thread(file_path.read_bytes)
        files = {"file": (file_path.name, file_bytes, content_type)}
        data = {
            "apply_vietnamese_corrections": str(apply_vietnamese_corrections).lower()
        }

        result = await self._post_multipart("/v1/ocr", files=files, data=data)
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Service returns "markdown" field (not "text")
        text = result.get("markdown") or result.get("text", "")

        return {
            "text": text,
            "pages": result.get("total_pages", result.get("pages", 1)),
            "processing_time_ms": processing_time_ms,
        }
