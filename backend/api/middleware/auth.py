"""API key authentication middleware.

Security considerations:
- API keys are ONLY accepted via the X-API-Key header, never query parameters.
  Query strings are logged in server access logs, browser history, proxy logs,
  and referrer headers, which exposes credentials to unauthorized parties.
- Timing-safe comparison prevents timing attacks that could leak key information
  by measuring response times with different key prefixes.
- Failed authentication attempts are logged with client IP and path for security
  monitoring and incident response, but the provided key is NEVER logged.
"""
import logging
import os
import secrets

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware to validate API key for protected endpoints.

    This middleware enforces API key authentication on all endpoints except
    health checks and CORS preflight requests. Keys must be provided via
    the X-API-Key header for security reasons.
    """

    async def dispatch(self, request: Request, call_next):
        """Process request and validate API key.

        Args:
            request: The incoming request
            call_next: The next middleware/handler in the chain

        Returns:
            Response from the next handler if authorized, or 401 JSONResponse if unauthorized
        """
        # Skip auth for health check and OPTIONS (CORS preflight)
        if request.url.path == "/health" or request.method == "OPTIONS":
            return await call_next(request)

        api_key = os.getenv("API_KEY")
        if not api_key:
            return await call_next(request)  # No key configured = no auth

        # Only accept API key from header - NEVER from query params
        # Query strings are logged in server logs, browser history, and proxies
        provided_key = request.headers.get("X-API-Key")

        # Use timing-safe comparison to prevent timing attacks
        if not provided_key or not secrets.compare_digest(provided_key, api_key):
            # Log auth failure with client info but NEVER log the actual key
            client_ip = request.client.host if request.client else "unknown"
            logger.warning(
                "Authentication failed: client_ip=%s path=%s",
                client_ip,
                request.url.path
            )
            # Cannot raise HTTPException in middleware - must return Response directly
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"}
            )

        return await call_next(request)
