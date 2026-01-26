"""
Authentication models for JWT token-based authentication.
"""
from pydantic import BaseModel, Field


class WsTokenRequest(BaseModel):
    """Request model for WebSocket token endpoint."""
    api_key: str = Field(..., description="API key to exchange for JWT tokens")


class TokenPayload(BaseModel):
    """JWT token payload structure."""
    sub: str = Field(..., description="Subject (user identifier)")
    jti: str = Field(..., description="JWT ID (unique token identifier)")
    type: str = Field(..., description="Token type (access or refresh)")
    exp: int = Field(..., description="Expiration timestamp (Unix epoch)")
    iat: int = Field(..., description="Issued at timestamp (Unix epoch)")
    iss: str = Field(..., description="Issuer")
    aud: str = Field(..., description="Audience")


class TokenResponse(BaseModel):
    """Response model for token generation endpoints."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")
    user_id: str = Field(..., description="User identifier")


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh endpoint."""
    refresh_token: str = Field(..., description="Refresh token")
