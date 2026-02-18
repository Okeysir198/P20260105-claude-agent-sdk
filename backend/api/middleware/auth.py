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
import secrets

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.settings import API_KEY
from api.services.token_service import token_service
from core.settings import get_settings

logger = logging.getLogger(__name__)

# Get centralized settings
_settings = get_settings()


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
        # Skip auth for health check, root path (load balancer), auth endpoints, and OPTIONS (CORS preflight)
        public_paths = set(_settings.api.public_paths)
        if request.url.path in public_paths or request.method == "OPTIONS":
            return await call_next(request)

        # Skip auth for webhook endpoints (called by external platform servers)
        if request.url.path.startswith("/api/v1/webhooks/"):
            return await call_next(request)

        if not API_KEY:
            return await call_next(request)  # No key configured = no auth

        # Only accept API key from header - NEVER from query params
        # Query strings are logged in server logs, browser history, and proxies
        provided_key = request.headers.get("X-API-Key")

        # Use timing-safe comparison to prevent timing attacks
        if not provided_key or not secrets.compare_digest(provided_key, API_KEY):
            # Log auth failure with client info but NEVER log the actual key
            client_ip = request.client.host if request.client else "unknown"
            logger.warning(f"Authentication failed: client_ip={client_ip} path={request.url.path}")
            # Cannot raise HTTPException in middleware - must return Response directly
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"}
            )

        # Extract user identity from X-User-Token header (optional)
        user_token = request.headers.get("X-User-Token")

        if user_token and token_service:
            try:
                # Decode token without type restriction - just verify signature and claims
                payload = token_service.decode_token_any_type(user_token)

                if payload and payload.get("username"):
                    # Store user context in request state
                    request.state.user = {
                        "user_id": payload.get("user_id", payload.get("sub")),
                        "username": payload.get("username", ""),
                        "role": payload.get("role", "user"),
                        "full_name": payload.get("full_name", ""),
                    }
            except Exception as e:
                # User token is optional, don't fail the request
                logger.debug(f"Failed to decode user token: {e}")

        return await call_next(request)
