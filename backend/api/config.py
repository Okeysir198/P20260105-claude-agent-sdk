"""API configuration settings."""
import hashlib
import hmac
import logging
import os
from pathlib import Path

from core.settings import get_settings

logger = logging.getLogger(__name__)

# Get centralized settings
_settings = get_settings()

# Centralized API key - used across all API modules
API_KEY = os.getenv("API_KEY")

# API server settings
API_CONFIG = {
    "host": os.getenv("API_HOST", _settings.api.host),
    "port": int(os.getenv("API_PORT", str(_settings.api.port))),
    "reload": os.getenv("API_RELOAD", "false").lower() == "true",
    "log_level": os.getenv("API_LOG_LEVEL", _settings.api.log_level),
    "cors_origins": os.getenv("CORS_ORIGINS", "*").split(",") if os.getenv("CORS_ORIGINS") else ["*"],
    "api_key": API_KEY,  # Optional API key for authentication
}

# Log warning if wildcard CORS is used
if "*" in API_CONFIG["cors_origins"]:
    logger.warning("WARNING: CORS configured with wildcard origin (*). Set CORS_ORIGINS for production.")

# JWT configuration
# Derive JWT secret from API_KEY using HMAC (secure key derivation)
def _get_jwt_secret() -> str | None:
    """Derive JWT secret from API_KEY using HMAC-SHA256."""
    if not API_KEY:
        return None

    # Derive JWT secret using HMAC-SHA256 with a fixed salt
    # This ensures API_KEY cannot be recovered from JWT secret
    salt = _settings.jwt.salt.encode()
    derived = hmac.new(salt, API_KEY.encode(), hashlib.sha256).hexdigest()
    return derived

JWT_CONFIG = {
    "secret_key": _get_jwt_secret(),
    "algorithm": _settings.jwt.algorithm,
    "access_token_expire_minutes": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
    "refresh_token_expire_days": int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")),
    "issuer": _settings.jwt.issuer,
    "audience": _settings.jwt.audience,
}

# Log JWT status
if JWT_CONFIG["secret_key"]:
    logger.info("JWT authentication enabled (using API_KEY as secret)")
else:
    logger.warning("API_KEY not configured. JWT authentication disabled.")

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
