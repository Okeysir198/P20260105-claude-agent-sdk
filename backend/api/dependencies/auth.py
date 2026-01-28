"""Authentication dependencies for FastAPI routes.

Provides dependency injection for user authentication context.
"""
import logging

from fastapi import HTTPException, Request

from api.models.user_auth import UserTokenPayload
from api.services.token_service import token_service

logger = logging.getLogger(__name__)


async def get_current_user(request: Request) -> UserTokenPayload:
    """Get current authenticated user from request state.

    Args:
        request: FastAPI request object

    Returns:
        UserTokenPayload with user information

    Raises:
        HTTPException: 401 if user is not authenticated
    """
    user_context = getattr(request.state, 'user', None)

    if not user_context:
        raise HTTPException(
            status_code=401,
            detail="User authentication required. Please login first."
        )

    return UserTokenPayload(
        user_id=user_context.get("user_id", ""),
        username=user_context.get("username", ""),
        role=user_context.get("role", "user"),
    )


async def get_current_user_optional(request: Request) -> UserTokenPayload | None:
    """Get current user if authenticated, None otherwise.

    Use this for endpoints that work differently for authenticated vs anonymous users.
    """
    user_context = getattr(request.state, 'user', None)

    if not user_context:
        return None

    return UserTokenPayload(
        user_id=user_context.get("user_id", ""),
        username=user_context.get("username", ""),
        role=user_context.get("role", "user"),
    )


async def get_current_user_ws(token: str) -> UserTokenPayload:
    """Get user from WebSocket JWT token.

    Args:
        token: JWT token from WebSocket query parameter

    Returns:
        UserTokenPayload with user information

    Raises:
        HTTPException: 401 if token is invalid or missing user claims
    """
    if not token_service:
        raise HTTPException(status_code=500, detail="Token service not configured")

    # Decode token without type restriction - verify signature and user claims only
    payload = token_service.decode_token_any_type(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    username = payload.get("username", "")
    if not username:
        raise HTTPException(status_code=401, detail="Token missing user identity")

    return UserTokenPayload(
        user_id=payload.get("user_id", payload.get("sub", "")),
        username=username,
        role=payload.get("role", "user"),
    )
