"""API configuration settings."""
import os
from pathlib import Path

# API server settings
API_CONFIG = {
    "host": os.getenv("API_HOST", "0.0.0.0"),
    "port": int(os.getenv("API_PORT", "7001")),
    "reload": os.getenv("API_RELOAD", "false").lower() == "true",
    "log_level": os.getenv("API_LOG_LEVEL", "info"),
    "cors_origins": os.getenv("CORS_ORIGINS", "*").split(",") if os.getenv("CORS_ORIGINS") else ["*"],
    "api_key": os.getenv("API_KEY"),  # Optional API key for authentication
}

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
