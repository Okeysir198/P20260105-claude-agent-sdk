"""JWT authentication utilities for WebSocket connections.

Provides JWT token validation for WebSocket endpoints.
"""
import logging
from typing import Optional, Tuple

from fastapi import WebSocket, status
from starlette.websockets import WebSocketDisconnect

from api.services.token_service import token_service

logger = logging.getLogger(__name__)


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

    # Try user_identity type first (for user login flow), then access type (for API key flow)
    payload = token_service.decode_and_validate_token(token, token_type="user_identity")
    if not payload:
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
