"""Platform identity to internal username mapping.

Maps platform-specific user identifiers to deterministic internal usernames
that plug directly into the existing per-user storage system.
"""

import hashlib

from platforms.base import Platform


def platform_identity_to_username(platform: Platform, platform_user_id: str) -> str:
    """Map a platform user identity to a deterministic internal username.

    The username is used as the data directory name under ``data/{username}/``.
    We use a short hash of the platform user ID to keep filenames sane while
    still being deterministic and collision-resistant.

    Args:
        platform: The messaging platform.
        platform_user_id: The user's platform-specific identifier.

    Returns:
        Internal username string, e.g. ``telegram_a3f9c12e``.
    """
    digest = hashlib.sha256(platform_user_id.encode()).hexdigest()[:8]
    return f"{platform.value}_{digest}"
