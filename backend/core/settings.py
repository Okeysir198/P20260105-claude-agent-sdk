# backend/core/settings.py
"""Centralized settings module for Claude Agent SDK.

This module provides a single source of truth for all configuration settings
across the application. Settings can be configured via environment variables.

Usage:
    from core.settings import get_settings

    settings = get_settings()
    print(settings.jwt.salt)
    print(settings.api.port)
    print(settings.storage.max_sessions)
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class JWTSettings(BaseSettings):
    """JWT-related configuration settings."""

    model_config = SettingsConfigDict(env_prefix="JWT_")

    salt: str = Field(
        default="claude-agent-sdk-jwt-v1",
        description="Salt used for deriving JWT secret from API key"
    )
    issuer: str = Field(
        default="claude-agent-sdk",
        description="JWT token issuer claim"
    )
    audience: str = Field(
        default="claude-agent-sdk-users",
        description="JWT token audience claim"
    )
    leeway_seconds: int = Field(
        default=60,
        description="Leeway in seconds for JWT expiration validation"
    )
    algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm"
    )


class APISettings(BaseSettings):
    """API server configuration settings."""

    model_config = SettingsConfigDict(env_prefix="API_")

    host: str = Field(
        default="0.0.0.0",
        description="Host to bind the API server to"
    )
    port: int = Field(
        default=7001,
        description="Port to bind the API server to"
    )
    public_paths: List[str] = Field(
        default=[
            "/",
            "/health",
            "/api/v1/auth/ws-token",
            "/api/v1/auth/ws-token-refresh",
            "/api/v1/auth/login"
        ],
        description="Paths that don't require API key authentication"
    )
    reload: bool = Field(
        default=False,
        description="Enable auto-reload for development"
    )
    log_level: str = Field(
        default="info",
        description="Logging level for the API server"
    )


class StorageSettings(BaseSettings):
    """Storage configuration settings."""

    model_config = SettingsConfigDict(env_prefix="STORAGE_")

    max_sessions: int = Field(
        default=20,
        description="Maximum number of sessions to keep per user"
    )
    sessions_filename: str = Field(
        default="sessions.json",
        description="Filename for session storage"
    )
    history_dirname: str = Field(
        default="history",
        description="Directory name for message history storage"
    )
    database_filename: str = Field(
        default="users.db",
        description="Filename for the SQLite user database"
    )


class EmailSettings(BaseSettings):
    """Email integration configuration settings."""

    model_config = SettingsConfigDict(env_prefix="EMAIL_")

    gmail_client_id: str | None = Field(
        default=None,
        description="Gmail OAuth client ID"
    )
    gmail_client_secret: str | None = Field(
        default=None,
        description="Gmail OAuth client secret"
    )
    gmail_redirect_uri: str = Field(
        default="http://localhost:7001/api/v1/email/gmail/callback",
        description="Gmail OAuth redirect URI"
    )
    # Yahoo uses app passwords (not OAuth) for IMAP access.
    # These fields are kept for potential future OAuth support but are not currently used.
    frontend_url: str = Field(
        default="http://localhost:7002",
        description="Frontend URL for OAuth redirects"
    )


class Settings(BaseSettings):
    """Root settings class containing all configuration sections."""

    model_config = SettingsConfigDict(env_prefix="", env_nested_delimiter="__")

    jwt: JWTSettings = Field(default_factory=JWTSettings)
    api: APISettings = Field(default_factory=APISettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Settings are cached for performance. The cache is populated on first call
    and reused for subsequent calls.

    Returns:
        Settings: The application settings instance.
    """
    return Settings()
