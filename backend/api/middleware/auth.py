"""API key authentication middleware.

API keys are ONLY accepted via X-API-Key header (never query params).
Uses timing-safe comparison to prevent timing attacks.
"""
import logging
import secrets

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from api.services.token_service import token_service
from core.settings import API_KEY, get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validates API key on all non-public endpoints via X-API-Key header."""

    async def dispatch(self, request: Request, call_next):
        public_paths = set(_settings.api.public_paths)
        if request.url.path in public_paths or request.method == "OPTIONS":
            return await call_next(request)

        if request.url.path.startswith("/api/v1/webhooks/"):
            return await call_next(request)

        if request.url.path.startswith("/api/v1/files/dl/"):
            return await call_next(request)

        if not API_KEY:
            return await call_next(request)

        provided_key = request.headers.get("X-API-Key")

        if not provided_key or not secrets.compare_digest(provided_key, API_KEY):
            client_ip = request.client.host if request.client else "unknown"
            logger.warning(f"Authentication failed: client_ip={client_ip} path={request.url.path}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"}
            )

        user_token = request.headers.get("X-User-Token")

        if user_token and token_service:
            try:
                payload = token_service.decode_token_any_type(user_token)

                if payload and payload.get("username"):
                    request.state.user = {
                        "user_id": payload.get("user_id", payload.get("sub")),
                        "username": payload.get("username", ""),
                        "role": payload.get("role", "user"),
                        "full_name": payload.get("full_name", ""),
                    }
            except Exception as e:
                logger.debug(f"Failed to decode user token: {e}")

        return await call_next(request)
