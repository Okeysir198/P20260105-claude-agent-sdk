"""Shared YAML configuration loader with caching."""
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


@lru_cache(maxsize=8)
def load_yaml_config(config_path: Path) -> dict[str, Any]:
    """Load and cache a YAML file. Returns empty dict if missing or empty."""
    if not config_path.exists():
        return {}

    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def clear_yaml_cache() -> None:
    """Clear the YAML configuration cache to force reload on next access."""
    load_yaml_config.cache_clear()
