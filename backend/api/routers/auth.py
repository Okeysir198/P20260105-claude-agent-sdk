"""Authentication router for JWT token management."""
import logging
import secrets

from fastapi import APIRouter, HTTPException, status

from core.settings import API_KEY
from api.models.auth import (
    WsTokenRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from api.services.token_service import token_service

router = APIRouter(prefix="/auth", tags=["authentication"])

logger = logging.getLogger(__name__)


@router.post("/ws-token", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def get_ws_token(request: WsTokenRequest) -> TokenResponse:
    """Exchange API key for short-lived JWT access + refresh tokens."""
    if not token_service:
        logger.error("JWT authentication attempted but JWT_SECRET_KEY not configured")
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="JWT authentication not enabled. Set JWT_SECRET_KEY environment variable.",
        )

    # Validate API key
    if not API_KEY or not secrets.compare_digest(request.api_key, API_KEY):
        logger.warning("WebSocket token request with invalid API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # Generate token pair
    try:
        tokens = token_service.create_token_pair(request.api_key)
        logger.info(f"WebSocket token issued for user: {tokens['user_id']}")
        return tokens
    except Exception as e:
        logger.error(f"Error creating tokens: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tokens",
        )


@router.post("/ws-token-refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_ws_token(request: RefreshTokenRequest) -> TokenResponse:
    """Refresh a WebSocket access token using a refresh token."""
    if not token_service:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="JWT authentication not enabled",
        )

    payload = token_service.decode_and_validate_token(
        request.refresh_token, token_type="refresh"
    )

    if not payload:
        logger.warning("Refresh token validation failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = payload.get("sub")

    try:
        token_service.revoke_token(payload.get("jti"))
        access_token, jti, expires_in = token_service.create_access_token(user_id)
        refresh_token = token_service.create_refresh_token(user_id)

        logger.info(f"Token refreshed for user: {user_id}")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "user_id": user_id,
        }
    except Exception as e:
        logger.error(f"Error refreshing tokens: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh tokens",
        )
