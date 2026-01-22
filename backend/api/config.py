"""API configuration settings."""
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# API server settings
API_CONFIG = {
    "host": os.getenv("API_HOST", "0.0.0.0"),
    "port": int(os.getenv("API_PORT", "7001")),
    "reload": os.getenv("API_RELOAD", "false").lower() == "true",
    "log_level": os.getenv("API_LOG_LEVEL", "info"),
    "cors_origins": os.getenv("CORS_ORIGINS", "*").split(",") if os.getenv("CORS_ORIGINS") else ["*"],
    "api_key": os.getenv("API_KEY"),  # Optional API key for authentication
}

# Log warning if wildcard CORS is used
if "*" in API_CONFIG["cors_origins"]:
    logger.warning("WARNING: CORS configured with wildcard origin (*). Set CORS_ORIGINS for production.")

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
