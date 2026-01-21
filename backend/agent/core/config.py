"""Configuration loader for Claude Agent SDK.

Loads environment and YAML configuration for provider settings.
"""
import os
from typing import Any

from dotenv import load_dotenv

from agent import PROJECT_ROOT
from agent.core.yaml_utils import load_yaml_config


def load_config() -> str:
    """Load environment and configuration, returning the active provider name."""
    load_dotenv(PROJECT_ROOT / ".env", override=True)

    config = load_yaml_config(PROJECT_ROOT / "config.yaml")

    provider = config.get("provider", "claude")

    if provider == "claude":
        return provider

    provider_config = config.get("providers", {}).get(provider, {})
    _configure_provider(provider_config)

    return provider


def _configure_provider(provider_config: dict[str, Any]) -> None:
    """Set environment variables for non-Claude providers."""
    if api_key := os.getenv(provider_config.get("env_key", "")):
        os.environ["ANTHROPIC_AUTH_TOKEN"] = api_key

    if base_url_env := provider_config.get("base_url_env"):
        if base_url := os.getenv(base_url_env):
            os.environ["ANTHROPIC_BASE_URL"] = base_url

    # Support default model override (e.g., for Ollama)
    if default_model_env := provider_config.get("default_model_env"):
        if default_model := os.getenv(default_model_env):
            os.environ["ANTHROPIC_MODEL"] = default_model


# Load config on module import
ACTIVE_PROVIDER = load_config()
