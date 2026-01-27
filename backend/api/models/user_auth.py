"""
User authentication models for login and user identity management.
"""
from pydantic import BaseModel
from typing import Literal


class LoginRequest(BaseModel):
    """Request model for user login endpoint."""
    username: str
    password: str


class UserInfo(BaseModel):
    """User information returned after successful authentication."""
    id: str
    username: str
    full_name: str | None
    role: Literal['admin', 'user']


class LoginResponse(BaseModel):
    """Response model for user login endpoint."""
    success: bool
    token: str | None = None      # JWT for user identification
    refresh_token: str | None = None
    user: UserInfo | None = None
    error: str | None = None


class UserTokenPayload(BaseModel):
    """Payload for user identity token (extracted from JWT)."""
    user_id: str
    username: str
    role: Literal['admin', 'user']
