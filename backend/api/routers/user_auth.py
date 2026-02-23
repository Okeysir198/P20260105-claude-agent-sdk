"""User authentication endpoints for login/logout with SQLite user database."""
import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from api.db.user_database import get_user_by_username, update_last_login, verify_password
from api.models.user_auth import LoginRequest, LoginResponse, UserInfo
from api.services.token_service import token_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["user-auth"])


class LogoutResponse(BaseModel):
    success: bool
    message: str


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    """Authenticate user and return JWT tokens."""
    if not verify_password(request.username, request.password):
        logger.warning(f"Failed login attempt for user: {request.username}")
        return LoginResponse(
            success=False,
            error="Invalid username or password"
        )

    user = get_user_by_username(request.username)
    if not user:
        return LoginResponse(success=False, error="User not found")

    if not user.is_active:
        return LoginResponse(success=False, error="Account is disabled")

    update_last_login(user.id)

    access_token, jti, expires_in = token_service.create_user_identity_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
        full_name=user.full_name,
    )
    refresh_token = token_service.create_refresh_token(user_id=user.id)

    logger.info(f"User logged in: {user.username}")

    return LoginResponse(
        success=True,
        token=access_token,
        refresh_token=refresh_token,
        user=UserInfo(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
        )
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(request: Request) -> LogoutResponse:
    """Logout user for audit purposes. Session invalidation happens client-side."""
    logger.info("User logged out")
    return LogoutResponse(success=True, message="Logged out successfully")


@router.get("/me", response_model=UserInfo)
async def get_current_user(request: Request) -> UserInfo:
    """Get current authenticated user info."""
    user_context = getattr(request.state, 'user', None)

    if not user_context:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return UserInfo(
        id=user_context.user_id,
        username=user_context.username,
        full_name=user_context.get('full_name'),
        role=user_context.role,
    )
