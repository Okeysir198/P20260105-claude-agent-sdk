"""Base HTTP client for media processing services.

Provides reusable HTTP/WebSocket client with error handling and timeout support.
"""
import httpx
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Common MIME type mappings shared across clients
MIME_TYPES: dict[str, str] = {
    # Images / documents
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "tiff": "image/tiff",
    "bmp": "image/bmp",
    "webp": "image/webp",
    # Audio
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "aac": "audio/aac",
    "flac": "audio/flac",
    "ogg": "audio/ogg",
    "opus": "audio/opus",
    "webm": "audio/webm",
}


def get_mime_type(filename: str, fallback: str = "application/octet-stream") -> str:
    """Get MIME type from a filename's extension.

    Args:
        filename: Filename or path string
        fallback: Default MIME type if extension is unrecognized
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return MIME_TYPES.get(ext, fallback)


class BaseServiceClient:
    """Base client for HTTP/WebSocket service communication.

    Handles common HTTP operations with timeout, error handling, and
    optional API key authentication.
    """

    def __init__(self, base_url: str, api_key: str | None = None, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=timeout)

    def _auth_headers(self, extra: dict | None = None) -> dict:
        """Build headers dict with auth token if configured."""
        headers = dict(extra) if extra else {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _post(self, endpoint: str, data: Any, **kwargs) -> dict:
        """Make a POST request with JSON data."""
        headers = self._auth_headers(kwargs.pop("headers", None))
        response = await self._client.post(
            f"{self.base_url}{endpoint}",
            json=data,
            headers=headers,
            **kwargs,
        )
        response.raise_for_status()
        return response.json()

    async def _post_multipart(self, endpoint: str, files: dict, data: dict | None = None) -> dict:
        """Make a multipart POST request (for file uploads)."""
        response = await self._client.post(
            f"{self.base_url}{endpoint}",
            headers=self._auth_headers(),
            files=files,
            data=data,
        )
        response.raise_for_status()
        return response.json()

    async def _get(self, endpoint: str, params: dict | None = None, **kwargs) -> dict:
        """Make a GET request."""
        headers = self._auth_headers(kwargs.pop("headers", None))
        response = await self._client.get(
            f"{self.base_url}{endpoint}",
            params=params,
            headers=headers,
            **kwargs,
        )
        response.raise_for_status()
        return response.json()

    async def _post_bytes(self, endpoint: str, content: bytes, **kwargs) -> bytes:
        """Make a POST request with raw bytes and return bytes response."""
        headers = self._auth_headers(kwargs.pop("headers", None))
        response = await self._client.post(
            f"{self.base_url}{endpoint}",
            content=content,
            headers=headers,
            **kwargs,
        )
        response.raise_for_status()
        return response.content

    async def _post_raw(self, endpoint: str, content: bytes, **kwargs) -> dict:
        """Make a POST request with raw bytes and return JSON response."""
        headers = self._auth_headers(kwargs.pop("headers", None))
        response = await self._client.post(
            f"{self.base_url}{endpoint}",
            content=content,
            headers=headers,
            **kwargs,
        )
        response.raise_for_status()
        return response.json()

    async def check_health(self, timeout: float = 2.0) -> str:
        """Quick health check. Returns 'available' or 'unavailable'."""
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    return "available"
        except Exception:
            pass
        return "unavailable"

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
