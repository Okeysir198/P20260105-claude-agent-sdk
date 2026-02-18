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
import hashlib
import hmac
import logging
import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

logger = logging.getLogger(__name__)


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

    model_config = SettingsConfigDict(
        env_prefix="EMAIL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    gmail_client_id: str | None = Field(
        default=None,
        description="Gmail OAuth client ID"
    )
    gmail_client_secret: str | None = Field(
        default=None,
        description="Gmail OAuth client secret"
    )
    gmail_redirect_uri: str | None = Field(
        default=None,
        description="Gmail OAuth redirect URI (e.g., https://claude-agent-sdk-chat.leanwise.ai/api/auth/callback/email/gmail)"
    )
    # Yahoo uses app passwords (not OAuth) for IMAP access.
    # These fields are kept for potential future OAuth support but are not currently used.
    frontend_url: str | None = Field(
        default=None,
        description="Frontend URL for OAuth redirects (e.g., https://claude-agent-sdk-chat.leanwise.ai)"
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


# --- Derived configuration (previously in api/config.py) ---

def get_api_key() -> str | None:
    """Get the API key from environment."""
    return os.getenv("API_KEY")


def _derive_jwt_secret(api_key: str | None) -> str | None:
    """Derive JWT secret from API_KEY using HMAC-SHA256."""
    if not api_key:
        return None
    settings = get_settings()
    salt = settings.jwt.salt.encode()
    return hmac.new(salt, api_key.encode(), hashlib.sha256).hexdigest()


def get_api_config() -> dict:
    """Get API server configuration dict."""
    settings = get_settings()
    api_key = get_api_key()
    cors_origins = os.getenv("CORS_ORIGINS", "*").split(",") if os.getenv("CORS_ORIGINS") else ["*"]

    if "*" in cors_origins:
        logger.warning("WARNING: CORS configured with wildcard origin (*). Set CORS_ORIGINS for production.")

    return {
        "host": os.getenv("API_HOST", settings.api.host),
        "port": int(os.getenv("API_PORT", str(settings.api.port))),
        "reload": os.getenv("API_RELOAD", "false").lower() == "true",
        "log_level": os.getenv("API_LOG_LEVEL", settings.api.log_level),
        "cors_origins": cors_origins,
        "api_key": api_key,
    }


def get_jwt_config() -> dict:
    """Get JWT configuration dict."""
    settings = get_settings()
    api_key = get_api_key()
    secret_key = _derive_jwt_secret(api_key)

    if secret_key:
        logger.info("JWT authentication enabled (using API_KEY as secret)")
    else:
        logger.warning("API_KEY not configured. JWT authentication disabled.")

    return {
        "secret_key": secret_key,
        "algorithm": settings.jwt.algorithm,
        "access_token_expire_minutes": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
        "refresh_token_expire_days": int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")),
        "issuer": settings.jwt.issuer,
        "audience": settings.jwt.audience,
    }


# Module-level singletons (evaluated once at import time, same as old api/config.py)
API_KEY = get_api_key()
API_CONFIG = get_api_config()
JWT_CONFIG = get_jwt_config()
