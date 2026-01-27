"""API configuration settings."""
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Centralized API key - used across all API modules
API_KEY = os.getenv("API_KEY")

# API server settings
API_CONFIG = {
    "host": os.getenv("API_HOST", "0.0.0.0"),
    "port": int(os.getenv("API_PORT", "7001")),
    "reload": os.getenv("API_RELOAD", "false").lower() == "true",
    "log_level": os.getenv("API_LOG_LEVEL", "info"),
    "cors_origins": os.getenv("CORS_ORIGINS", "*").split(",") if os.getenv("CORS_ORIGINS") else ["*"],
    "api_key": API_KEY,  # Optional API key for authentication
}

# Log warning if wildcard CORS is used
if "*" in API_CONFIG["cors_origins"]:
    logger.warning("WARNING: CORS configured with wildcard origin (*). Set CORS_ORIGINS for production.")

# JWT configuration
# Derive JWT secret from API_KEY using HMAC (secure key derivation)
def _get_jwt_secret():
    """Derive JWT secret from API_KEY using HMAC-SHA256."""
    import hashlib
    import hmac

    if not API_KEY:
        return None

    # Derive JWT secret using HMAC-SHA256 with a fixed salt
    # This ensures API_KEY cannot be recovered from JWT secret
    salt = b"claude-agent-sdk-jwt-v1"
    derived = hmac.new(salt, API_KEY.encode(), hashlib.sha256).hexdigest()
    return derived

JWT_CONFIG = {
    "secret_key": _get_jwt_secret(),
    "algorithm": "HS256",
    "access_token_expire_minutes": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
    "refresh_token_expire_days": int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")),
    "issuer": "claude-agent-sdk",
    "audience": "claude-agent-sdk-users",
}

# Log JWT status
if JWT_CONFIG["secret_key"]:
    logger.info("JWT authentication enabled (using API_KEY as secret)")
else:
    logger.warning("API_KEY not configured. JWT authentication disabled.")

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
