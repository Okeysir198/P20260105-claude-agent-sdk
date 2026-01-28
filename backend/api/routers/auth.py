"""Authentication router for JWT token management."""
import logging
import secrets

from fastapi import APIRouter, HTTPException, status

from api.config import API_KEY
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
    """Exchange API key for JWT tokens for WebSocket authentication.

    This endpoint accepts an API key and returns an access token and refresh token.
    The access token is short-lived (30 minutes) and used for WebSocket authentication.
    The refresh token is long-lived (7 days) and used to obtain new access tokens.

    Args:
        request: WebSocket token request with API key

    Returns:
        TokenResponse with access_token, refresh_token, expires_in, user_id

    Raises:
        HTTPException: If JWT is not configured or API key is invalid
    """
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
    """Refresh a WebSocket access token using a refresh token.

    Args:
        request: Refresh request with refresh_token

    Returns:
        TokenResponse with new access_token, new refresh_token, expires_in, user_id

    Raises:
        HTTPException: If JWT is not configured or refresh token is invalid
    """
    if not token_service:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="JWT authentication not enabled",
        )

    # Validate refresh token
    payload = token_service.decode_and_validate_token(
        request.refresh_token, token_type="refresh"
    )

    if not payload:
        logger.warning("Refresh token validation failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Get user ID from token
    user_id = payload.get("sub")

    # Generate new token pair
    try:
        # Revoke old refresh token
        old_jti = payload.get("jti")
        token_service.revoke_token(old_jti)

        # Create new tokens
        # Note: We use user_id directly since we don't have the original API key
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
