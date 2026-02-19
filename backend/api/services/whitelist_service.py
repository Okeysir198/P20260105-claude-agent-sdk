"""Platform whitelist service.

Controls which phone numbers are allowed to interact with platform agents.
Stores whitelist entries in data/.config/platform_whitelist.json.
"""

import json
import logging
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from agent.core.storage import get_data_dir

logger = logging.getLogger(__name__)

WHITELIST_FILENAME = "platform_whitelist.json"
CONFIG_DIR_NAME = ".config"


def _normalize_phone(phone: str) -> str:
    """Strip +, spaces, dashes from phone number for consistent comparison."""
    return re.sub(r"[\s+\-()]", "", phone)


def _get_config_dir() -> Path:
    """Get the admin config directory, creating it if needed."""
    config_dir = get_data_dir() / CONFIG_DIR_NAME
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def _get_whitelist_path() -> Path:
    return _get_config_dir() / WHITELIST_FILENAME


def _default_whitelist() -> dict[str, Any]:
    return {
        "enabled": {
            "whatsapp": False,
            "telegram": False,
            "zalo": False,
            "imessage": False,
        },
        "entries": [],
    }


def _seed_from_env(data: dict[str, Any]) -> bool:
    """Seed whitelist entries from PLATFORM_USER_MAP_* env vars.

    Only adds entries that don't already exist. Returns True if any were added.
    """
    prefix = "PLATFORM_USER_MAP_"
    existing_keys = {
        f"{e['platform']}:{_normalize_phone(e['phone_number'])}"
        for e in data.get("entries", [])
    }

    added = False
    for key, username in os.environ.items():
        if not key.startswith(prefix):
            continue
        rest = key[len(prefix):]
        parts = rest.split("_", 1)
        if len(parts) != 2:
            continue
        platform = parts[0].lower()
        phone = _normalize_phone(parts[1])
        lookup = f"{platform}:{phone}"

        if lookup not in existing_keys:
            data["entries"].append({
                "id": str(uuid.uuid4()),
                "platform": platform,
                "phone_number": phone,
                "label": f"Seeded from env ({key})",
                "mapped_username": username.strip(),
                "created_at": datetime.now().isoformat(),
            })
            existing_keys.add(lookup)
            added = True
            logger.info(f"Seeded whitelist entry: {platform}:{phone} -> {username}")

    return added


class WhitelistService:
    """In-memory cached whitelist with file-backed persistence."""

    def __init__(self) -> None:
        self._data: dict[str, Any] | None = None
        # Fast lookup cache: platform -> set of normalized phone numbers
        self._cache: dict[str, set[str]] | None = None

    def _load(self) -> dict[str, Any]:
        """Load whitelist from disk, seeding from env on first run."""
        if self._data is not None:
            return self._data

        path = _get_whitelist_path()
        if path.exists():
            try:
                loaded = json.loads(path.read_text())
                self._data = loaded
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error reading whitelist file: {e}")
                self._data = _default_whitelist()
        else:
            self._data = _default_whitelist()
            _seed_from_env(self._data)
            self._save()

        assert self._data is not None
        return self._data

    def _save(self) -> None:
        """Persist whitelist to disk and invalidate cache."""
        if self._data is None:
            return
        path = _get_whitelist_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._data, indent=2))
        self._cache = None

    def _build_cache(self) -> dict[str, set[str]]:
        """Build lookup cache from entries."""
        if self._cache is not None:
            return self._cache

        data = self._load()
        cache: dict[str, set[str]] = {}
        for entry in data.get("entries", []):
            platform = entry["platform"]
            phone = _normalize_phone(entry["phone_number"])
            cache.setdefault(platform, set()).add(phone)
        self._cache = cache
        return self._cache

    def is_allowed(self, platform: str, phone_number: str) -> bool:
        """Check if a phone number is allowed for the given platform.

        Returns True if:
        - Whitelist is disabled for this platform (open mode), OR
        - The phone number is in the whitelist
        """
        data = self._load()
        enabled = data.get("enabled", {})
        if not enabled.get(platform, False):
            return True  # Whitelist disabled = all allowed

        cache = self._build_cache()
        normalized = _normalize_phone(phone_number)
        return normalized in cache.get(platform, set())

    def get_mapped_username(self, platform: str, phone_number: str) -> str | None:
        """Get the mapped username for a whitelisted phone number."""
        data = self._load()
        normalized = _normalize_phone(phone_number)
        for entry in data.get("entries", []):
            if (
                entry["platform"] == platform
                and _normalize_phone(entry["phone_number"]) == normalized
                and entry.get("mapped_username")
            ):
                return entry["mapped_username"]
        return None

    def list_entries(self) -> dict[str, Any]:
        """Return full whitelist data (enabled flags + entries)."""
        return self._load()

    def add_entry(
        self,
        platform: str,
        phone_number: str,
        label: str = "",
        mapped_username: str = "",
    ) -> dict[str, Any]:
        """Add a new whitelist entry. Returns the created entry."""
        data = self._load()
        entry = {
            "id": str(uuid.uuid4()),
            "platform": platform,
            "phone_number": _normalize_phone(phone_number),
            "label": label,
            "mapped_username": mapped_username,
            "created_at": datetime.now().isoformat(),
        }
        data["entries"].append(entry)
        self._save()
        return entry

    def remove_entry(self, entry_id: str) -> bool:
        """Remove a whitelist entry by ID. Returns True if found and removed."""
        data = self._load()
        original_len = len(data["entries"])
        data["entries"] = [e for e in data["entries"] if e["id"] != entry_id]
        if len(data["entries"]) < original_len:
            self._save()
            return True
        return False

    def set_enabled(self, platform: str, enabled: bool) -> None:
        """Enable or disable whitelist for a platform."""
        data = self._load()
        data.setdefault("enabled", {})
        data["enabled"][platform] = enabled
        self._save()

    def invalidate_cache(self) -> None:
        """Force reload from disk on next access."""
        self._data = None
        self._cache = None


# Singleton instance
_whitelist_service: WhitelistService | None = None


def get_whitelist_service() -> WhitelistService:
    """Get the singleton whitelist service."""
    global _whitelist_service
    if _whitelist_service is None:
        _whitelist_service = WhitelistService()
    return _whitelist_service
