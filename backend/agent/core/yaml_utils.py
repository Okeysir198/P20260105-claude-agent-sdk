"""Shared YAML configuration loader with caching.

Provides a centralized, cached YAML loading utility for configuration files.
"""
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


@lru_cache(maxsize=8)
def load_yaml_config(config_path: Path) -> dict[str, Any]:
    """Load and cache YAML configuration.

    Uses LRU cache to avoid repeated file reads for the same configuration.
    The cache is based on the file path, so each unique config file is
    cached separately.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Parsed YAML content as a dictionary, or empty dict if file doesn't exist
        or is empty.
    """
    if not config_path.exists():
        return {}

    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def clear_yaml_cache() -> None:
    """Clear the YAML configuration cache.

    Call this if configuration files have been modified and need to be reloaded.
    """
    load_yaml_config.cache_clear()
