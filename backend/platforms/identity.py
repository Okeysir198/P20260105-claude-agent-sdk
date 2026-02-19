"""Platform identity to internal username mapping.

Maps platform-specific user identifiers to deterministic internal usernames
that plug directly into the existing per-user storage system.

Supports explicit mappings via:
1. Whitelist JSON file entries with mapped_username (primary)
2. {PLATFORM}_WHITELIST env vars (comma-separated, default to 'admin')
3. PLATFORM_USER_MAP_* env vars (custom username overrides)

Example env vars:
  WHATSAPP_WHITELIST=84907996550,84123456789
  PLATFORM_USER_MAP_WHATSAPP_84907996550=admin
"""

import hashlib
import os
import re

from platforms.base import Platform

# Lazy-loaded explicit mapping cache
_EXPLICIT_MAP: dict[str, str] | None = None

_SUPPORTED_PLATFORMS = {"whatsapp", "telegram", "zalo", "imessage"}


def _normalize_phone(phone: str) -> str:
    """Strip +, spaces, dashes from phone number."""
    return re.sub(r"[\s+\-()]", "", phone)


def _get_explicit_map() -> dict[str, str]:
    """Load identity mappings from whitelist JSON + env vars (cached)."""
    global _EXPLICIT_MAP
    if _EXPLICIT_MAP is not None:
        return _EXPLICIT_MAP

    _EXPLICIT_MAP = {}

    # 1. Load from whitelist JSON file (primary source)
    try:
        from api.services.whitelist_service import get_whitelist_service
        service = get_whitelist_service()
        data = service.list_entries()
        for entry in data.get("entries", []):
            mapped = entry.get("mapped_username", "")
            if mapped:
                platform = entry["platform"]
                phone = entry["phone_number"]
                _EXPLICIT_MAP[f"{platform}:{phone}"] = mapped
    except Exception:
        pass  # Whitelist service not available yet during early startup

    # 2. Parse {PLATFORM}_WHITELIST env vars (all map to 'admin')
    whitelist_suffix = "_WHITELIST"
    for key, value in os.environ.items():
        if not key.endswith(whitelist_suffix):
            continue
        platform_name = key[: -len(whitelist_suffix)].lower()
        if platform_name not in _SUPPORTED_PLATFORMS:
            continue
        for raw_phone in value.split(","):
            phone = _normalize_phone(raw_phone.strip())
            if not phone:
                continue
            lookup = f"{platform_name}:{phone}"
            if lookup not in _EXPLICIT_MAP:
                _EXPLICIT_MAP[lookup] = "admin"

    # 3. Overlay PLATFORM_USER_MAP_* env vars (can override)
    prefix = "PLATFORM_USER_MAP_"
    for key, username in os.environ.items():
        if not key.startswith(prefix):
            continue
        rest = key[len(prefix):]
        parts = rest.split("_", 1)
        if len(parts) != 2:
            continue
        platform_name = parts[0].lower()
        platform_user_id = parts[1]
        _EXPLICIT_MAP[f"{platform_name}:{platform_user_id}"] = username

    return _EXPLICIT_MAP


def invalidate_identity_cache() -> None:
    """Invalidate the identity mapping cache. Call when whitelist changes."""
    global _EXPLICIT_MAP
    _EXPLICIT_MAP = None


def platform_identity_to_username(platform: Platform, platform_user_id: str) -> str:
    """Map a platform user identity to an internal username.

    Checks explicit mappings (whitelist JSON + env vars) first,
    then falls back to a deterministic hash-based username.
    """
    explicit = _get_explicit_map()
    lookup_key = f"{platform.value}:{platform_user_id}"
    if username := explicit.get(lookup_key):
        return username

    digest = hashlib.sha256(platform_user_id.encode()).hexdigest()[:8]
    return f"{platform.value}_{digest}"
