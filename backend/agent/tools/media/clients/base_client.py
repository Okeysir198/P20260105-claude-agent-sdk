"""Base HTTP client for media processing services.

Provides reusable HTTP/WebSocket client with error handling and timeout support.
"""
import httpx
import logging
from typing import Any

logger = logging.getLogger(__name__)


class BaseServiceClient:
    """Base client for HTTP/WebSocket service communication.

    Handles common HTTP operations with timeout, error handling, and
    optional API key authentication.
    """

    def __init__(self, base_url: str, api_key: str | None = None, timeout: float = 120.0):
        """Initialize the base client.

        Args:
            base_url: Base URL of the service (e.g., "http://localhost:18013")
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds (default: 120)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=timeout)

    async def _post(self, endpoint: str, data: Any, **kwargs) -> dict:
        """Make a POST request with JSON data.

        Args:
            endpoint: API endpoint path (e.g., "/v1/ocr")
            data: JSON-serializable data to send
            **kwargs: Additional httpx.request parameters

        Returns:
            Parsed JSON response

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        headers = kwargs.pop("headers", {})
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = await self._client.post(
            f"{self.base_url}{endpoint}",
            json=data,
            headers=headers,
            **kwargs
        )
        response.raise_for_status()
        return response.json()

    async def _post_multipart(self, endpoint: str, files: dict, data: dict | None = None) -> dict:
        """Make a multipart POST request (for file uploads).

        Args:
            endpoint: API endpoint path
            files: Files dict for multipart upload
            data: Optional form data fields

        Returns:
            Parsed JSON response

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = await self._client.post(
            f"{self.base_url}{endpoint}",
            headers=headers,
            files=files,
            data=data
        )
        response.raise_for_status()
        return response.json()

    async def _get(self, endpoint: str, params: dict | None = None, **kwargs) -> dict:
        """Make a GET request.

        Args:
            endpoint: API endpoint path
            params: Query parameters
            **kwargs: Additional httpx.request parameters

        Returns:
            Parsed JSON response

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        headers = kwargs.pop("headers", {})
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = await self._client.get(
            f"{self.base_url}{endpoint}",
            params=params,
            headers=headers,
            **kwargs
        )
        response.raise_for_status()
        return response.json()

    async def _post_bytes(self, endpoint: str, content: bytes, **kwargs) -> bytes:
        """Make a POST request with raw bytes and return bytes response.

        Useful for TTS services that return audio data.

        Args:
            endpoint: API endpoint path
            content: Raw bytes to send
            **kwargs: Additional httpx.request parameters

        Returns:
            Raw response bytes

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        headers = kwargs.pop("headers", {})
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = await self._client.post(
            f"{self.base_url}{endpoint}",
            content=content,
            headers=headers,
            **kwargs
        )
        response.raise_for_status()
        return response.content

    async def check_health(self, timeout: float = 2.0) -> str:
        """Quick health check for the service.

        Args:
            timeout: Connection timeout in seconds

        Returns:
            "available" if service responds, "unavailable" otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    return "available"
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, Exception):
            pass
        return "unavailable"

    async def close(self) -> None:
        """Close the HTTP client.

        Should be called when done with the client to properly release resources.
        """
        await self._client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
