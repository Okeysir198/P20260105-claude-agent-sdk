"""JWT authentication middleware and utilities.

All endpoints require JWT token authentication.
JWT tokens are extracted from the Authorization header for REST API calls.
"""
import logging
from typing import Optional, Tuple

from fastapi import Request, WebSocket, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.websockets import WebSocketDisconnect

from api.config import JWT_CONFIG
from api.services.token_service import token_service

logger = logging.getLogger(__name__)

# Security scheme for OpenAPI docs
security = HTTPBearer(auto_error=True)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to validate JWT tokens for protected endpoints.

    This middleware enforces JWT authentication on all endpoints except
    health checks, auth endpoints, and CORS preflight requests.
    """

    async def dispatch(self, request: Request, call_next):
        """Process request and validate JWT token.

        Args:
            request: The incoming request
            call_next: The next middleware/handler in the chain

        Returns:
            Response from the next handler if authorized, or 401 JSONResponse if unauthorized
        """
        # Skip auth for health check, auth endpoints, and OPTIONS (CORS preflight)
        public_paths = {"/health", "/api/v1/auth/ws-token", "/api/v1/auth/ws-token-refresh"}
        if (
            request.url.path in public_paths
            or request.method == "OPTIONS"
        ):
            return await call_next(request)

        # Ensure JWT is configured
        if not token_service:
            logger.error("JWT authentication attempted but JWT_SECRET_KEY not configured")
            return JSONResponse(
                status_code=500,
                content={"detail": "JWT authentication not configured. Set JWT_SECRET_KEY environment variable."},
            )

        # Extract and validate JWT token
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            client_ip = request.client.host if request.client else "unknown"
            logger.warning(
                "Missing JWT token: client_ip=%s path=%s",
                client_ip,
                request.url.path,
            )
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required. Provide JWT token in Authorization header."},
            )

        token = auth_header.split(" ")[1]
        payload = token_service.decode_and_validate_token(token, token_type="access")

        if not payload:
            client_ip = request.client.host if request.client else "unknown"
            logger.warning(
                "Invalid JWT token: client_ip=%s path=%s",
                client_ip,
                request.url.path,
            )
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired JWT token"},
            )

        # Add user info to request state
        request.state.user_id = payload.get("sub")
        request.state.jti = payload.get("jti")

        return await call_next(request)


async def validate_websocket_token(
    websocket: WebSocket,
    token: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Validate WebSocket connection authentication.

    Args:
        websocket: The WebSocket connection
        token: JWT token from query parameter

    Returns:
        Tuple of (user_id, jti) if authenticated

    Raises:
        WebSocketDisconnect: If authentication fails
    """
    # Ensure JWT is configured
    if not token_service:
        logger.error("JWT authentication not configured")
        await websocket.close(
            code=status.WS_1011_INTERNAL_ERROR,
            reason="JWT authentication not configured",
        )
        raise WebSocketDisconnect(
            code=status.WS_1011_INTERNAL_ERROR,
            reason="JWT authentication not configured",
        )

    # Validate JWT token
    if not token:
        client_host = websocket.client.host if websocket.client else "unknown"
        logger.warning(f"WebSocket connection missing token: client={client_host}")
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication token required",
        )
        raise WebSocketDisconnect(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication token required",
        )

    payload = token_service.decode_and_validate_token(token, token_type="access")

    if not payload:
        client_host = websocket.client.host if websocket.client else "unknown"
        logger.warning(f"WebSocket JWT authentication failed: client={client_host}")
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid or expired JWT token",
        )
        raise WebSocketDisconnect(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid or expired JWT token",
        )

    user_id = payload.get("sub")
    jti = payload.get("jti")
    logger.debug(f"WebSocket authenticated with JWT: user={user_id}")

    return user_id, jti
