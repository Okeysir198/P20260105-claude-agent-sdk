"""API key authentication middleware."""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import os


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware to validate API key for protected endpoints."""

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

        # Check header or query param
        provided_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        if provided_key != api_key:
            # Cannot raise HTTPException in middleware - must return Response directly
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"}
            )

        return await call_next(request)
