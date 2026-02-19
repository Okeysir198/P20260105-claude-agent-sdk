"""Platform settings service.

Manages runtime-configurable platform settings with fallback chain:
JSON file value -> env var -> hardcoded default.

Stores settings in data/.config/platform_settings.json.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

from agent.core.storage import get_data_dir

logger = logging.getLogger(__name__)

SETTINGS_FILENAME = "platform_settings.json"
CONFIG_DIR_NAME = ".config"

# Setting definitions: key -> (env_var_name, hardcoded_default)
_SETTING_DEFS: dict[str, tuple[str, Any]] = {
    "default_agent_id": ("PLATFORM_DEFAULT_AGENT_ID", None),
    "session_max_age_hours": ("PLATFORM_SESSION_MAX_AGE_HOURS", 24),
}


def _get_settings_path() -> Path:
    config_dir = get_data_dir() / CONFIG_DIR_NAME
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / SETTINGS_FILENAME


class SettingsService:
    """File-backed platform settings with env var fallback."""

    def __init__(self) -> None:
        self._data: dict[str, Any] | None = None

    def _load(self) -> dict[str, Any]:
        if self._data is not None:
            return self._data

        path = _get_settings_path()
        if path.exists():
            try:
                loaded = json.loads(path.read_text())
                self._data = loaded
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error reading settings file: {e}")
                self._data = {}
        else:
            self._data = {}
            self._save()

        assert self._data is not None
        return self._data

    def _save(self) -> None:
        if self._data is None:
            return
        path = _get_settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._data, indent=2))

    def get(self, key: str) -> Any:
        """Get a setting value with fallback chain: file -> env -> default."""
        data = self._load()

        # 1. Check JSON file
        if key in data and data[key] is not None:
            return data[key]

        # 2. Check env var
        if key in _SETTING_DEFS:
            env_name, default = _SETTING_DEFS[key]
            env_val = os.getenv(env_name)
            if env_val is not None:
                # Type coerce based on default type
                if isinstance(default, int):
                    try:
                        return int(env_val)
                    except ValueError:
                        pass
                return env_val

            # 3. Hardcoded default
            return default

        return None

    def set(self, key: str, value: Any) -> None:
        """Set a setting value (persisted to file)."""
        data = self._load()
        data[key] = value
        self._save()

    def get_all(self) -> dict[str, Any]:
        """Get all settings with resolved values (file -> env -> default)."""
        result = {}
        for key in _SETTING_DEFS:
            result[key] = self.get(key)
        return result

    def update_all(self, settings: dict[str, Any]) -> None:
        """Update multiple settings at once."""
        data = self._load()
        for key, value in settings.items():
            if key in _SETTING_DEFS:
                data[key] = value
        self._save()

    def invalidate_cache(self) -> None:
        """Force reload from disk on next access."""
        self._data = None


# Singleton instance
_settings_service: SettingsService | None = None


def get_settings_service() -> SettingsService:
    """Get the singleton settings service."""
    global _settings_service
    if _settings_service is None:
        _settings_service = SettingsService()
    return _settings_service
