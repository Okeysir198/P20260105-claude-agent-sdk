"""OCR client for Ollama GLM-OCR service.

Extracts text from images and PDFs with Vietnamese correction support.
"""
import logging
from pathlib import Path

from .base_client import BaseServiceClient
from ..config import OCR_SERVICE_URL, OCR_API_KEY

logger = logging.getLogger(__name__)


class OCRClient(BaseServiceClient):
    """Client for Ollama GLM-OCR service.

    Provides OCR capabilities for images and PDFs with layout detection,
    semantic tagging, and optional Vietnamese text corrections.
    """

    def __init__(self, base_url: str = OCR_SERVICE_URL, api_key: str | None = None):
        """Initialize the OCR client.

        Args:
            base_url: OCR service URL (default: from config)
            api_key: Optional API key (default: from config)
        """
        super().__init__(base_url, api_key or OCR_API_KEY or None)

    async def process_file(
        self,
        file_path: Path,
        apply_vietnamese_corrections: bool = False,
    ) -> dict:
        """Process a file through OCR.

        Args:
            file_path: Path to image or PDF file
            apply_vietnamese_corrections: Whether to apply Vietnamese text corrections

        Returns:
            Dict with:
                - text: Extracted text content
                - pages: Number of pages processed
                - processing_time_ms: Processing time in milliseconds

        Raises:
            FileNotFoundError: If file doesn't exist
            httpx.HTTPStatusError: If OCR service request fails
        """
        import time

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Determine content type
        content_type = self._get_content_type(file_path)

        start_time = time.time()

        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, content_type)}
            data = {
                "apply_vietnamese_corrections": str(apply_vietnamese_corrections).lower()
            }

            result = await self._post_multipart("/v1/ocr", files=files, data=data)

        processing_time_ms = int((time.time() - start_time) * 1000)

        return {
            "text": result.get("text", ""),
            "pages": result.get("pages", 1),
            "processing_time_ms": processing_time_ms,
        }

    def _get_content_type(self, file_path: Path) -> str:
        """Get MIME type for file.

        Args:
            file_path: Path to file

        Returns:
            MIME type string
        """
        ext = file_path.suffix.lstrip(".").lower()

        mime_types = {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "tiff": "image/tiff",
            "bmp": "image/bmp",
            "webp": "image/webp",
        }

        return mime_types.get(ext, "application/octet-stream")
