"""Platform identity to internal username mapping.

Maps platform-specific user identifiers to deterministic internal usernames
that plug directly into the existing per-user storage system.

Supports explicit mappings via PLATFORM_USER_MAP_* env vars so specific
platform users can share data with existing internal users (e.g. admin).

Example: PLATFORM_USER_MAP_WHATSAPP_84907996550=admin
"""

import hashlib
import os

from platforms.base import Platform

# Lazy-loaded explicit mapping cache
_EXPLICIT_MAP: dict[str, str] | None = None


def _get_explicit_map() -> dict[str, str]:
    """Load PLATFORM_USER_MAP_* env vars into a mapping dict (cached)."""
    global _EXPLICIT_MAP
    if _EXPLICIT_MAP is not None:
        return _EXPLICIT_MAP

    _EXPLICIT_MAP = {}
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


def platform_identity_to_username(platform: Platform, platform_user_id: str) -> str:
    """Map a platform user identity to an internal username.

    Checks explicit env-var mappings first, then falls back to a
    deterministic hash-based username.
    """
    explicit = _get_explicit_map()
    lookup_key = f"{platform.value}:{platform_user_id}"
    if username := explicit.get(lookup_key):
        return username

    digest = hashlib.sha256(platform_user_id.encode()).hexdigest()[:8]
    return f"{platform.value}_{digest}"
