"""JWT authentication utilities for WebSocket connections.

Provides JWT token validation for WebSocket endpoints.
"""
import logging

from fastapi import WebSocket, status

from api.services.token_service import token_service

logger = logging.getLogger(__name__)


class WebSocketAuthError(Exception):
    """Raised when WebSocket authentication fails."""


async def validate_websocket_token(
    websocket: WebSocket,
    token: str | None = None,
) -> tuple[str, str]:
    """
    Validate WebSocket connection authentication.

    Args:
        websocket: The WebSocket connection
        token: JWT token from query parameter

    Returns:
        Tuple of (user_id, jti) if authenticated

    Raises:
        WebSocketAuthError: If authentication fails
    """
    if not token_service:
        logger.error("JWT authentication not configured")
        await websocket.close(
            code=status.WS_1011_INTERNAL_ERROR,
            reason="JWT authentication not configured",
        )
        raise WebSocketAuthError("JWT authentication not configured")

    client_host = websocket.client.host if websocket.client else "unknown"

    if not token:
        logger.warning(f"WebSocket connection missing token: client={client_host}")
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication token required",
        )
        raise WebSocketAuthError("Authentication token required")

    payload = token_service.decode_token_any_type(token)

    if not payload:
        logger.warning(f"WebSocket JWT authentication failed: client={client_host}")
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid or expired JWT token",
        )
        raise WebSocketAuthError("Invalid or expired JWT token")

    user_id = payload.get("sub")
    jti = payload.get("jti")
    logger.debug(f"WebSocket authenticated with JWT: user={user_id}")

    return user_id, jti
